import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from app.models.actions import ClickAction, FillAction, NavigateAction, SubmitAction, WaitAction, ActionProposal, ActionType
from app.models.state import DataClass, DestinationClass, TrustLevel, Verdict
from app.policy.engine import PolicyContext, PolicyEngine
from app.provenance.provenance import DataRef
from app.agent.planner import validate_action_shape
from app.security.registry import DataRegistry


def ctx(**kw):
    base = dict(
        action_type=ActionType.CLICK,
        action_label="test",
        destination=DestinationClass.SAME_ORIGIN,
        destination_host="account.localhost",
        page_trust=TrustLevel.TRUSTED,
        data=[],
        induced=False,
        has_transfer=False,
    )
    base.update(kw)
    return PolicyContext(**base)


def dref(data_class=DataClass.PUBLIC, ph="[X_1]"):
    return DataRef(ph=ph, data_class=data_class, origin_host="account.localhost", origin_trust=TrustLevel.TRUSTED)


ENGINE = PolicyEngine()


class TestPolicyMatrix:
    def test_ordinary_click_allows(self):
        e = ENGINE.evaluate(ctx())
        assert e.verdict == Verdict.ALLOW and e.policy_ids == ["ORDINARY_CLICK"]

    def test_sensitive_submit_requires_approval(self):
        e = ENGINE.evaluate(
            ctx(action_type=ActionType.SUBMIT, data=[dref(DataClass.PERSONAL)], destination=DestinationClass.SAME_ORIGIN)
        )
        assert e.verdict == Verdict.APPROVAL
        assert "SENSITIVE_SUBMISSION" in e.policy_ids

    def test_secret_external_transfer_blocks(self):
        e = ENGINE.evaluate(
            ctx(
                action_type=ActionType.FILL,
                data=[dref(DataClass.SECRET)],
                destination=DestinationClass.EXTERNAL,
                destination_host="vendor.localhost",
                has_transfer=True,
            )
        )
        assert e.verdict == Verdict.BLOCK
        assert "SECRET_EXTERNAL_TRANSFER" in e.policy_ids

    def test_induced_exfiltration_blocks(self):
        e = ENGINE.evaluate(
            ctx(
                action_type=ActionType.FILL,
                data=[dref(DataClass.CREDENTIAL)],
                destination=DestinationClass.EXTERNAL,
                destination_host="vendor.localhost",
                induced=True,
                has_transfer=True,
            )
        )
        assert e.verdict == Verdict.BLOCK
        assert "INDUCED_EXFILTRATION" in e.policy_ids

    def test_canary_fill_external_blocks(self):
        e = ENGINE.evaluate(
            ctx(
                action_type=ActionType.FILL,
                data=[dref(DataClass.CANARY)],
                destination=DestinationClass.EXTERNAL,
                destination_host="vendor.localhost",
                has_transfer=True,
            )
        )
        assert e.verdict == Verdict.BLOCK
        assert "CLASSIFIED_TRANSFER" in e.policy_ids

    def test_unknown_destination_fails_closed(self):
        e = ENGINE.evaluate(ctx(destination=DestinationClass.UNKNOWN))
        assert e.verdict == Verdict.BLOCK
        assert e.fail_closed and "UNKNOWN_DESTINATION" in e.policy_ids

    def test_unverified_fails_closed(self):
        # EXTRACT to internal with sensitive data -> nothing authorizes
        e = ENGINE.evaluate(ctx(action_type=ActionType.EXTRACT, data=[dref(DataClass.CREDENTIAL)], destination=DestinationClass.INTERNAL))
        assert e.verdict == Verdict.BLOCK
        assert "UNVERIFIED_AUTHORIZATION" in e.policy_ids

    def test_public_read_allows(self):
        e = ENGINE.evaluate(ctx(action_type=ActionType.EXTRACT, destination=DestinationClass.SAME_ORIGIN))
        assert e.verdict == Verdict.ALLOW

    def test_navigate_internal_allows(self):
        e = ENGINE.evaluate(ctx(action_type=ActionType.NAVIGATE, destination=DestinationClass.INTERNAL))
        assert e.verdict == Verdict.ALLOW

    def test_external_navigate_requires_approval(self):
        e = ENGINE.evaluate(ctx(action_type=ActionType.NAVIGATE, destination=DestinationClass.EXTERNAL))
        assert e.verdict == Verdict.APPROVAL

    def test_block_precedence_over_approval(self):
        # Data contains SECRET moving externally AND form submit: BLOCK wins.
        e = ENGINE.evaluate(
            ctx(
                action_type=ActionType.SUBMIT,
                data=[dref(DataClass.SECRET), dref(DataClass.PERSONAL)],
                destination=DestinationClass.EXTERNAL,
                destination_host="vendor.localhost",
                has_transfer=True,
            )
        )
        assert e.verdict == Verdict.BLOCK

    def test_untrusted_page_cannot_drive_transfer(self):
        e = ENGINE.evaluate(
            ctx(
                action_type=ActionType.FILL,
                data=[dref(DataClass.EMAIL)],
                destination=DestinationClass.INTERNAL,
                page_trust=TrustLevel.UNTRUSTED,
                has_transfer=True,
            )
        )
        assert e.verdict == Verdict.BLOCK and "UNTRUSTED_PAGE_FLOW" in e.policy_ids


class TestActionShapeValidation:
    def test_click_ok(self):
        p = ActionProposal(action_id="a1", generation=0, proposed_by="T", action=ClickAction(action_type=ActionType.CLICK, selector="#read-more", label="Read"))
        ok, _ = validate_action_shape(p)
        assert ok

    def test_bad_selector_rejected(self):
        p = ActionProposal(action_id="a2", generation=0, proposed_by="T", action=ClickAction(action_type=ActionType.CLICK, selector="#x()", label="Bad"))
        ok, errs = validate_action_shape(p)
        assert not ok and any("selector" in e for e in errs)

    def test_inject_selector_rejected(self):
        p = ActionProposal(action_id="a3", generation=0, proposed_by="T", action=ClickAction(action_type=ActionType.CLICK, selector="#x:has(div)", label="Bad"))
        ok, errs = validate_action_shape(p)
        assert not ok

    def test_navigate_external_rejected(self):
        p = ActionProposal(
            action_id="a4", generation=0, proposed_by="T",
            action=NavigateAction(action_type=ActionType.NAVIGATE, url="https://evil.example.com/x", label="Nav"),
        )
        ok, errs = validate_action_shape(p)
        assert not ok and any("not allowed" in e for e in errs)

    def test_fill_needs_value_or_ref(self):
        p = ActionProposal(action_id="a5", generation=0, proposed_by="T", action=FillAction(action_type=ActionType.FILL, selector="#f", value="", placeholder_ref="", label="f"))
        ok, errs = validate_action_shape(p)
        assert not ok

    def test_fill_with_placeholder_ok(self):
        p = ActionProposal(action_id="a6", generation=0, proposed_by="T", action=FillAction(action_type=ActionType.FILL, selector="#f", placeholder_ref="[SECRET_1]", label="f"))
        ok, _ = validate_action_shape(p)
        assert ok

    def test_wait_range(self):
        bad = ActionProposal(action_id="a7", generation=0, proposed_by="T", action=WaitAction(action_type=ActionType.WAIT, duration_ms=9999999, label="w"))
        ok, _ = validate_action_shape(bad)
        assert not ok


class TestExecutorGating:
    async def test_rejects_stale_generation(self):
        from app.browser.executor import Authorization, Executor, ExecutionError, AuthorizationPurpose

        class Boom:
            async def page_for(self, *a):
                raise AssertionError("should never reach page")

        p = ActionProposal(action_id="a", generation=1, proposed_by="T", action=WaitAction(action_type=ActionType.WAIT, label="w"))
        auth = Authorization(auth_id="au", session_id="s", generation=0, action_id="a", purpose=AuthorizationPurpose.ALLOW)
        res = await Executor(Boom(), DataRegistry()).execute("s", p, auth)
        assert not res.ok and res.error_code == ExecutionError.REJECTED

    async def test_rejects_wrong_action(self):
        from app.browser.executor import Authorization, Executor, ExecutionError, AuthorizationPurpose

        class Boom:
            async def page_for(self, *a):
                raise AssertionError("should never reach page")

        p = ActionProposal(action_id="a", generation=0, proposed_by="T", action=WaitAction(action_type=ActionType.WAIT, label="w"))
        auth = Authorization(auth_id="au", session_id="s", generation=0, action_id="OTHER", purpose=AuthorizationPurpose.ALLOW)
        res = await Executor(Boom(), DataRegistry()).execute("s", p, auth)
        assert not res.ok and res.error_code == ExecutionError.REJECTED

    async def test_rejects_consumed_auth(self):
        from app.browser.executor import Authorization, Executor, ExecutionError, AuthorizationPurpose

        class Boom:
            async def page_for(self, *a):
                raise AssertionError("should never reach page")

        p = ActionProposal(action_id="a", generation=0, proposed_by="T", action=WaitAction(action_type=ActionType.WAIT, label="w"))
        auth = Authorization(auth_id="au", session_id="s", generation=0, action_id="a", purpose=AuthorizationPurpose.ALLOW, consumed=True)
        res = await Executor(Boom(), DataRegistry()).execute("s", p, auth, consume_cb=lambda *a: True)
        assert not res.ok and res.error_code == ExecutionError.REJECTED

    async def test_single_use_consume_cb(self):
        from app.browser.executor import Authorization, Executor, AuthorizationPurpose

        class StubPage:
            async def wait_for_timeout(self, ms):
                return None

            @property
            def url(self):
                return "about:blank"

            async def title(self):
                return "stub"

        class StubBrowser:
            async def page_for(self, *a):
                return StubPage()

        spent = [False]
        p = ActionProposal(action_id="a", generation=0, proposed_by="T", action=WaitAction(action_type=ActionType.WAIT, label="w"))
        auth = Authorization(auth_id="au", session_id="s", generation=0, action_id="a", purpose=AuthorizationPurpose.APPROVED)
        ex = Executor(StubBrowser(), DataRegistry())

        def consume(aid, sid, gen, act):
            if spent[0]:
                return False
            spent[0] = True
            return True

        res = await ex.execute("s", p, auth, consume_cb=consume)
        assert res.ok  # first use executes (and spends the token)
        assert spent[0]
        res2 = await ex.execute("s", p, auth, consume_cb=consume)
        assert not res2.ok and res2.error_code == "REJECTED"  # second use refused


class TestApprovalExpiry:
    def test_pending_approval_expired(self):
        from app.models.approval import PendingApproval

        pa = PendingApproval(action_id="x", generation=0, expiry=time.time() - 5, proposal={}, decision={}, provenance=[])
        assert pa.expired