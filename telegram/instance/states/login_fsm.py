from aiogram.fsm import state


class LoginFSM(state.StatesGroup):
    access_parameter = state.State()
    password = state.State()
