

class envdsRunTransitionException(Exception):
    def __init__(self, state: str="UNKNOWN") -> None:
        self.message = f"Run state {state} is already being changed"
        super().__init__(self.message)

class envdsRunErrorException(Exception):
    def __init__(self, state: str="UNKNOWN") -> None:
        self.message = f"Run state {state} failed"
        super().__init__(self.message)

class envdsRunWaitException(Exception):
    def __init__(self, state: str="UNKNOWN") -> None:
        self.message = f"Waiting for run state before {state}"
        super().__init__(self.message)
