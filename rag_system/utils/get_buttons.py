from rag_system.models import Roles
from miniapp.models import ChatSession


def get_buttons(session: ChatSession):
    if session.mode == ChatSession.SKYNET and session.current_role is not None:
        return {"buttons": ["/ЧАТ"]}
    elif session.mode == ChatSession.SKYNET and session.current_role is None:
        return {
            "roles": [
                {"role_name": role.name, "role_id": role.id}
                for role in Roles.objects.all()
            ]
        }
    return {"buttons": ["/Тренажер"]}
