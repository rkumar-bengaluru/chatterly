class TaskContext:

    def __init__(self, task, timeout, order, status):
        self.task = task 
        self.timeout = timeout 
        self.order = order 
        self.status = status 
        self.subtasks = []