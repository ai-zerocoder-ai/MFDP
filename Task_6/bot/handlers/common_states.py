from aiogram.fsm.state import State, StatesGroup

class TattooGenStates(StatesGroup):
    GET_PROMPT = State()
    CONFIRM = State()
