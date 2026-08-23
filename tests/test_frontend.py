from pathlib import Path


ROOT = Path(__file__).parents[1]
SRC = ROOT / "frontend" / "src"
MAIN = SRC / "main.tsx"
API = SRC / "api.ts"
TOAST = SRC / "toast.tsx"
AUTH = SRC / "auth.tsx"
HOME = SRC / "home.tsx"
CREATE = SRC / "create-session.tsx"
SESSION = SRC / "session-screen.tsx"
LEADERBOARD = SRC / "leaderboard.tsx"
STYLES = SRC / "styles.css"
INDEX_HTML = ROOT / "frontend" / "index.html"
VITE_CONFIG = ROOT / "frontend" / "vite.config.ts"
NGINX_CONF = ROOT / "frontend" / "nginx.conf"

SCREEN_FILES = [AUTH, HOME, CREATE, SESSION, LEADERBOARD]


def test_all_screens_reachable_from_main_routing():
    source = MAIN.read_text()

    for path in ("auth", "home", "create-session", "session-screen", "leaderboard"):
        assert f'from "./{path}"' in source
    assert "prototype" not in source


def test_main_refreshes_me_after_login():
    source = MAIN.read_text()

    assert "setMe(await api.me())" in source


def test_prototype_file_removed():
    assert not (SRC / "room-prototype.tsx").exists()


def test_auth_screens_cover_register_and_login():
    source = AUTH.read_text()

    assert "api.login(" in source
    assert "api.register(" in source
    assert "password" in source
    assert "username" in source
    assert "Log in" in source
    assert "Register" in source


def test_home_screen_has_join_create_and_recent_sessions():
    source = HOME.read_text()
    main_source = MAIN.read_text()

    assert "api.recentSessions()" in source
    assert "api.getSession(" in source
    assert "New session" in source
    assert "Join" in source
    assert "api.logout(" in main_source


def test_create_session_screen_has_game_capacity_timeout():
    source = CREATE.read_text()

    assert "api.games()" in source
    assert "api.createSession(" in source
    assert "capacity" in source
    assert "timeout" in source


def test_create_session_shows_actual_default_timeout():
    source = CREATE.read_text()

    assert "default_timeout_minutes" in source
    assert "Game default" in source


def test_session_screen_promotes_prototype_with_score_actions_and_states():
    source = SESSION.read_text()

    for action in ("+1", "+5", "+10", "Custom"):
        assert action in source
    for state in ("setup", "live", "timed_out", "finalized", "discarded"):
        assert state in source
    assert "/events" in source
    assert "api.joinSession(" in source
    assert "api.finalizeSession(" in source
    assert "api.discardSession(" in source
    assert "api.startSession(" in source
    assert "api.updateScore(" in source


def test_session_screen_uses_active_membership_and_guards_stream():
    source = SESSION.read_text()

    assert "p.active && p.user_id === me?.id" in source
    assert "isActiveMember" in source
    assert "!isHost && !isActiveMember" in source
    assert "No live connection" in source


def test_leaderboard_screen_shows_ranked_rows():
    source = LEADERBOARD.read_text()

    assert "api.games()" in source
    assert "api.leaderboard(" in source
    assert "rank" in source
    assert "games played" in source.lower()


def test_leaderboard_screen_no_global_option():
    source = LEADERBOARD.read_text()
    api_source = API.read_text()

    assert "api.globalLeaderboard(" not in source
    assert "All games" not in source
    assert "globalLeaderboard" not in api_source
    assert "api.leaderboard(" in source
    assert "api.games()" in source


def test_toast_notification_component_exists():
    source = TOAST.read_text()

    assert "ToastProvider" in source
    assert "useToast" in source
    for screen in (AUTH, HOME, CREATE, SESSION, LEADERBOARD):
        assert "useToast" in screen.read_text()


def test_screens_use_flexbox_not_grid():
    for path in SCREEN_FILES + [MAIN]:
        assert "grid" not in path.read_text()


def test_uses_tailwind_and_mobile_viewport():
    styles = STYLES.read_text()
    index_html = INDEX_HTML.read_text()
    vite_config = VITE_CONFIG.read_text()

    assert '@import "tailwindcss"' in styles
    assert "viewport" in index_html
    assert 'content="width=device-width, initial-scale=1' in index_html
    assert "tailwindcss" in vite_config
    assert "flex" in SESSION.read_text()


def test_nginx_disables_caching_for_index_html():
    conf = NGINX_CONF.read_text()

    assert "Cache-Control" in conf
    assert "no-cache" in conf
    assert "index.html" in conf
