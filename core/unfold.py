from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

UNFOLD = {
    "SITE_TITLE": "КУДА?",
    "SITE_HEADER": "КУДА?",
    "SITE_URL": "/",
    "SITE_SYMBOL": "person",
    "SITE_DROPDOWN": [
        {
            "icon": "diamond",
            "title": _("Ewa Бот"),
            "link": "https://t.me/ewahelpertestbot",
        },
    ],
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": False,
    "ENVIRONMENT": "main.environment_callback",
    "ENVIRONMENT_TITLE_PREFIX": "main.environment_title_prefix_callback",
    "STYLES": [
        lambda request: static("/css/style.css"),
    ],
    "SCRIPTS": [
        lambda request: static("js/script.js"),
    ],
    "BORDER_RADIUS": "10px",
    "COLORS": {
        "base": {
            # Neutral colors matching Flutter's scaffoldBackgroundColor/light gray/white
            "50": "248 250 252",  # F8FAFC - Flutter's light scaffoldBackground
            "100": "240 244 248",  # F0F4F8 - Flutter's input fill
            "200": "224 230 237",  # E0E6ED - Flutter's enabled border
            "300": "209 217 230",  # D1D9E6 - Lighter gray
            "400": "176 190 204",  # B0BECC - Even darker gray
            "500": "140 150 170",  # 8C96AA - Neutral mid gray
            "600": "108 120 140",  # 6C788C - Gray for dark surface contrast
            "700": "70 80 100",  # 465064 - Deep gray
            "800": "34 38 47",  # 22262F - Flutter's dark surface
            "900": "16 20 26",  # 10141A - Flutter's dark scaffoldBackground
            "950": "0 0 0",  # Pure black
        },
        "primary": {
            # Blue accent as in Flutter (Color(0xFF1C77FF))
            "50": "237 244 255",  # EDF4FF - Very light blue
            "100": "201 223 255",  # C9DFFF - Lighter blue
            "200": "158 199 255",  # 9EC7FF
            "300": "93 162 255",  # 5DA2FF
            "400": "28 119 255",  # 1C77FF - Flutter's blue accent
            "500": "24 96 204",  # 1860CC - Slightly deeper
            "600": "18 79 168",  # 124FA8
            "700": "13 62 133",  # 0D3E85
            "800": "8 38 90",  # 08265A
            "900": "4 21 51",  # 041533
            "950": "2 10 25",  # 020A19
        },
        "secondary": {
            # Green accent as in Flutter (Color(0xFF20DF7F))
            "50": "229 251 240",  # E5FBF0
            "100": "176 244 217",  # B0F4D9
            "200": "102 236 184",  # 66ECB8
            "300": "53 223 127",  # 35DF7F
            "400": "32 223 127",  # 20DF7F - Flutter's green accent
            "500": "30 190 100",  # 1EBE64
            "600": "28 170 90",  # 1CAA5A
            "700": "23 133 70",  # 178546
            "800": "14 94 50",  # 0E5E32
            "900": "7 47 25",  # 072F19
            "950": "2 13 6",  # 020D06
        },
        "error": {
            # Red accent for errors (Flutter uses Colors.redAccent)
            "50": "255 235 238",  # FFEbee
            "100": "255 205 210",  # FFCDD2
            "200": "239 83 80",  # EF5350
            "300": "229 57 53",  # E53935
            "400": "244 67 54",  # F44336 (Material red)
            "500": "229 28 35",  # E51C23 (Red accent)
            "600": "198 40 40",  # C62828
            "700": "183 28 28",  # B71C1C
            "800": "97 13 13",  # 610D0D
            "900": "40 0 0",  # 280000
            "950": "20 0 0",  # 140000
        },
    },
    "SIDEBAR": {
        "show_search": False,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "🧭 Навигация",
                "separator": False,
                "collapsible": False,
                "items": [
                    {
                        "title": "📊 Панель управления",
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
            {
                "title": "👥 Профили",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "👤 Профили",
                        "icon": "person",
                        "link": reverse_lazy(
                            "admin:telegram_client_botclient_changelist"
                        ),
                    },
                    {
                        "title": "💬 Сессия клиента бота",
                        "icon": "person",
                        "link": reverse_lazy(
                            "admin:telegram_client_botclientsession_changelist"
                        ),
                    },
                ],
            },
            {
                "title": "💭 Сессии чата",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "💬 Сессии",
                        "icon": "chat",
                        "link": reverse_lazy("admin:miniapp_chatsession_changelist"),
                    },
                    {
                        "title": "💌 Сообщения",
                        "icon": "forum",
                        "link": reverse_lazy("admin:miniapp_message_changelist"),
                    },
                ],
            },
            {
                "title": "🌳 Дерево кнопок",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "🔘 Кнопки",
                        "icon": "account_tree",
                        "link": reverse_lazy("admin:telegram_buttontree_changelist"),
                    },
                    {
                        "title": "📎 Материалы кнопок",
                        "icon": "attach_file",
                        "link": reverse_lazy(
                            "admin:telegram_attachmenttobutton_changelist"
                        ),
                    },
                    {
                        "title": "📁 Файлы материалов",
                        "icon": "folder",
                        "link": reverse_lazy(
                            "admin:telegram_attachmentdata_changelist"
                        ),
                    },
                ],
            },
            {
                "title": "💊 BAD Тест",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "❓ Вопросы теста",
                        "icon": "quiz",
                        "link": reverse_lazy(
                            "admin:telegram_badtestquestion_changelist"
                        ),
                    },
                    {
                        "title": "💊 Продукты БАД",
                        "icon": "medication",
                        "link": reverse_lazy(
                            "admin:telegram_badtestproduct_changelist"
                        ),
                    },
                    {
                        "title": "📋 Сессии тестирования",
                        "icon": "history",
                        "link": reverse_lazy(
                            "admin:telegram_badtestsession_changelist"
                        ),
                    },
                ],
            },
            {
                "title": "🧠 RAG система",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "📊 Эмбеддинг",
                        "icon": "scatter_plot",
                        "link": reverse_lazy("admin:rag_system_embedding_changelist"),
                    },
                    {
                        "title": "🛠️ Утилиты",
                        "icon": "build",
                        "link": reverse_lazy("admin:rag_system_utils_changelist"),
                    },
                    {
                        "title": "🎭 Роли",
                        "icon": "group",
                        "link": reverse_lazy("admin:rag_system_roles_changelist"),
                    },
                ],
            },
        ],
    },
}
