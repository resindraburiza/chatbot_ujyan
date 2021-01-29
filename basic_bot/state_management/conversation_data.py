class ConversationData:
    def __init__(self, channel_id=None, test_id=None, test_title=None,
        on_test_session=False, on_submit_session=False, on_register_complete=False, on_complete_answer=False,
        counter=1, problem_set=[], answers={}):
        self.channel_id = channel_id
        self.test_id = test_id
        self.test_title = test_title
        self.on_test_session = on_test_session
        self.on_submit_session = on_submit_session
        self.on_register_complete = on_register_complete
        self.on_complete_answer = on_complete_answer
        self.counter = counter
        self.problem_set = problem_set
        self.answers = answers