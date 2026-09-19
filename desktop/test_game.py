import io
import queue
from types import SimpleNamespace

from game import MACRO_FRAMES, App, Enemy, Game, Shot, demo_action


def test_jump_lands_on_one_way_platform():
    g = Game()
    g.x = 260
    g.step("jump_right")
    lowest = g.y
    for _ in range(90):
        g.step("wait")
        lowest = min(lowest, g.y)
    assert lowest < 170
    assert g.y == 224
    assert g.grounded


def test_scroll_requires_height_not_just_x():
    g = Game()
    g.x = 510
    g.step()
    assert g.collected == 0
    g.y = 178
    g.step()
    assert g.collected == 1


def test_rescue_requires_all_scrolls():
    g = Game()
    g.x = 2520
    g.step()
    assert g.status == "playing"
    for scroll in g.scrolls:
        scroll[2] = True
    g.step()
    assert g.status == "won"


def test_damage_has_invulnerability_window():
    g = Game()
    g.damage()
    g.damage()
    assert g.hp == 4
    for _ in range(80):
        g.step()
    g.damage()
    assert g.hp == 3


def test_sword_kills_and_deflects():
    g = Game()
    g.enemies = [Enemy(g.x + 32)]
    g.shots = [Shot(g.x + 30, g.y - 17, -155, True)]
    g.step("slash")
    assert g.kills == 1
    assert not g.shots
    assert g.hp == 5


def test_throw_cooldown_prevents_every_frame_shots():
    g = Game()
    g.enemies = []
    for _ in range(12):
        g.step("throw_right")
    assert len(g.shots) == 1


def test_entire_level_can_be_completed():
    g = Game()
    for _ in range(1800):
        g.step(demo_action(g))
        if g.status != "playing":
            break
    assert g.status == "won"
    assert g.collected == 3
    assert g.hp > 0


def ai_app():
    app = App.__new__(App)
    app.game = Game()
    app.mode = "ai"
    app.worker = SimpleNamespace(results=queue.Queue(), requests=queue.Queue())
    app.generation = 4
    app.busy = True
    app.paused = False
    app.error = ""
    app.frames_left = 0
    app.calls = 1
    app.limit = 2
    app.log = io.StringIO()
    app.action = "wait"
    app.key_dialog = False
    return app


def test_ai_wait_freezes_world():
    app = ai_app()
    state = app.game.state()
    for _ in range(60):
        app.tick()
    assert app.game.elapsed == 0
    assert app.game.state() == state


def test_stale_reply_after_restart_is_discarded():
    app = ai_app()
    app.worker.results.put((3, "right", {}, 0.9, 80, None))
    app.tick()
    assert app.game.x == 64
    assert app.action == "wait"
    generation, _ = app.worker.requests.get_nowait()
    assert generation == 4


def test_successful_ai_reply_advances_exact_macro():
    app = ai_app()
    app.worker.results.put((4, "right", {"right": 1.0}, 0.9, 80, None))
    for _ in range(MACRO_FRAMES):
        app.tick()
    assert abs(app.game.x - (64 + 145 * MACRO_FRAMES / 60)) < 0.001
    assert app.frames_left == 0


def test_api_failure_pauses_but_manual_still_works():
    app = ai_app()
    app.worker.results.put((4, None, {}, 0, 0, "429 rate limited"))
    app.tick()
    assert app.error
    assert app.game.elapsed == 0
    app.set_mode("manual")
    app.tick((1, False, False, False))
    assert app.game.x > 64


def test_session_budget_is_not_reset_by_restart():
    app = ai_app()
    app.key = "test-placeholder"
    app.calls = app.limit
    app.busy = False
    app.restart()
    app.tick()
    assert app.error
    assert app.worker.requests.empty()


def test_missing_key_opens_dialog_without_api_call(monkeypatch):
    import game

    monkeypatch.setattr(game.pg.key, "start_text_input", lambda: None)
    app = ai_app()
    app.key = None
    app.worker = None
    app.set_mode("ai")
    app.tick()
    assert app.key_dialog
    assert app.calls == 1
    assert app.game.elapsed == 0


def test_vercel_key_is_rejected_before_call():
    app = ai_app()
    app.key_buffer = "vck_test_placeholder"
    app.key_dialog = True
    app.submit_key()
    assert app.key_dialog
    assert "Vercel" in app.key_error
    assert app.worker.requests.empty()


def test_submitting_key_connects_without_saving_secret(monkeypatch):
    import game

    monkeypatch.setattr(game.pg.key, "stop_text_input", lambda: None)
    workers = []

    def make_worker(key):
        worker = SimpleNamespace(results=queue.Queue(), requests=queue.Queue())
        workers.append(worker)
        return worker

    monkeypatch.setattr(game, "JevWorker", make_worker)
    app = ai_app()
    app.worker = None
    app.key_buffer = "apikey_test_placeholder_not_real"
    app.key_dialog = True
    app.submit_key()
    app.tick()
    assert not app.key_dialog
    assert not app.key_buffer
    assert app.busy
    assert len(workers) == 1
    _, state = workers[0].requests.get_nowait()
    assert "apikey_" not in str(state)
    assert "apikey_" not in app.log.getvalue()


def test_jev_worker_real_sdk_contract_with_mock_transport(monkeypatch):
    import typesafe_sdk

    from game import JevWorker

    received = []

    def request(self, *, state, questions):
        received.append((state, questions))
        return SimpleNamespace(
            choices={
                "action": SimpleNamespace(
                    choice="jump_throw_right",
                    probabilities={"jump_throw_right": 0.8},
                    confidence=0.7,
                )
            }
        )

    monkeypatch.setattr(typesafe_sdk.TypeSafeClient, "system_one", request)
    worker = JevWorker("apikey_test_placeholder_not_real")
    worker.requests.put((1, Game().state()))
    result = worker.results.get(timeout=3)
    worker.close()
    worker.thread.join(timeout=3)
    assert result[0:2] == (1, "jump_throw_right")
    assert result[-1] is None
    assert received[0][1]["action"].criteria["jump_throw_right"]
