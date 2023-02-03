

class envdsRunTransitionException(Exception):
    def __init__(self, state: str="UNKNOWN") -> None:
        self.message = f"Run state {state} is already being changed"
        super().__init__(self.message)
