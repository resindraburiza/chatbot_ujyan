# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from botbuilder.core import ActivityHandler, TurnContext, CardFactory, MessageFactory
from botbuilder.schema import ChannelAccount, HeroCard, CardImage, CardAction, ActionTypes, ActivityTypes
import asyncio
import aiohttp
import os
import json

class MyBot(ActivityHandler):
    def __init__(self):
        self.counter = 1
        self.problem_set = []
        self.answers = {}
        self.student_ID = ''
        self.student_name = ''
        self.test_ID = ''
        self.test_title = ''
        self.on_test_session = False
        self.on_submit_session = False
        self.on_register_complete = False
        self.session = aiohttp.ClientSession()

        # API endpoint
        # self.API_base = 'https://virtserver.swaggerhub.com/AgentOfChange/ninemillion/1.0.0'
        self.API_base = 'https://ujiyan-web-app.azurewebsites.net/'
        # self.API_base = 'https://gist.githubusercontent.com/wawando/3073a175b3111cb966670497e6a951cf/raw/b8e968077a40c3344f4c99442a1b3a4689941e06/'

    # See https://aka.ms/about-bot-activity-message to learn more about the message and other activity types.

    async def reset_and_submit(self):
        # sumbit
        submit_url = os.path.join(self.API_base,'submissions','create')

        # answer dict creation
        answers = []
        _keys = sorted(self.answers.keys())
        for _key in _keys:
            answers.append({'answer':self.answers[_key]['ans'], 'problem_id':self.answers[_key]['q_id']})

        # params = {'student_id':self.student_ID, 'test_id':self.test_ID, 'submissions':json.dumps(answers)}
        params = {'student_id':self.student_ID, 'test_id':self.test_ID, 'submissions': answers}
        print(submit_url)
        print(params)
        resp = await self.session.post(submit_url, json=params)
        print(resp.status)
        # reset
        self.problem_set = []
        self.counter = 1
        self.answers = {}
        # self.student_ID = ''
        # self.student_name = ''
        self.test_ID = ''
        self.test_title = ''
        self.on_test_session = False
        self.on_submit_session = False

    async def asign_test_ID(self, test_id):
        self.test_ID = test_id

    async def switch_on_test_session(self):
        self.on_test_session = ~self.on_test_session

    async def switch_on_submit_session(self):
        self.on_submit_session = ~self.on_submit_session

    async def parse_problem_set(self, json_dump):
        self.test_title = json_dump['title']
        print(json_dump['problems'])
        self.problem_set.extend(json_dump['problems'])
        print(self.problem_set)

    async def get_problems(self, problem_id):
        target_path = os.path.join(self.API_base, 'tests', problem_id)
        # target_path = self.API_base
        print(target_path)
        async with self.session.get(target_path) as resp:
            status = resp.status
            print(status)
            response =  await resp.json()
        return status, response

    async def register_student(self):
        path = self.API_base
        path = os.path.join(path,'students')
        async with self.session.post(path, json={'name':self.student_name}) as resp:
            data = await resp.json()
            self.student_ID = data['id']

    async def get_student_id(self):
        return self.student_ID

    async def count_up(self):
        self.counter = min(self.counter+1, len(self.problem_set))

    async def count_down(self):
        self.counter = max(self.counter-1, 1)

    async def get_stored_answer(self):
        return self.answers[-1].lower()

    async def update_collected_answer(self, answer, q_id):
        self.answers[str(self.counter)] = {'q_id':q_id, 'ans':answer}
        await self.count_up()

    async def on_message_activity(self, turn_context: TurnContext):
        if turn_context.activity.text is not None:
            user_input = turn_context.activity.text
        else:
            user_input = None

        if not self.on_register_complete:
            await self.__send_registration_card(turn_context)

        elif (not self.on_test_session and not self.on_submit_session) and user_input[0]!='#':
            await self.__send_intro_card(turn_context)
        
        # check test ID
        elif (not self.on_test_session and not self.on_submit_session) and user_input[0]=='#':
            test_id = user_input[1:]
            if len(test_id) != 8:
                await turn_context.send_activity("Test ID should be 6-digits number")
            else:
                status, to_parse = await self.get_problems(test_id)
                if status == 404:
                    await turn_context.send_activity(f"Test ID of {test_id} is not found. Please insert the correct test ID")
                else:
                    await self.asign_test_ID(test_id)
                    await self.parse_problem_set(to_parse)
                    await turn_context.send_activity(f"Test titled {to_parse['title'].capitalize()} found. There are {len(self.problem_set)} question(s). Type anything to start the test.")
                    await self.switch_on_test_session()

        # start test session
        elif self.on_test_session and not self.on_submit_session:
            if turn_context.activity.text is not None:
                if turn_context.activity.text.lower() == 'submit':
                    await self.switch_on_test_session()
                    await self.switch_on_submit_session()
                    await self.__on_submit_activity(turn_context)
                else:
                    await self.__send_question_card(turn_context)
            elif turn_context.activity.value is not None:
                _answer = turn_context.activity.value['ans']
                _context = turn_context.activity.value['msg']
                _question_id = turn_context.activity.value['q_id']
                if _answer == 'BACK': 
                    await self.count_down()
                    await turn_context.send_activity("Go back one question")
                elif _answer == 'NEXT':
                    await self.count_up()
                    await turn_context.send_activity("Go forward one question")
                else:
                    await turn_context.send_activity(f"Answered with { _context }")
                    await self.update_collected_answer(_answer, _question_id)
                await self.__send_question_card(turn_context)
            else:
                await self.__send_question_card(turn_context)
        
        # start submission session
        elif not self.on_test_session and self.on_submit_session:
            await self.__on_submit_activity(turn_context)

    async def on_members_added_activity(
        self,
        members_added: ChannelAccount,
        turn_context: TurnContext
    ):
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("Hello and welcome to this test-taking chatbot! Please input your name to register.")

    async def __send_registration_card(self, turn_context: TurnContext):
        if turn_context.activity.text is not None:
            self.student_name = turn_context.activity.text
            card = HeroCard(
                title="Your name is:",
                text=f"{ self.student_name }",
                buttons=[
                    CardAction(type=ActionTypes.message_back, title='Yes', value=True),
                    CardAction(type=ActionTypes.message_back, title='No', value=False)
                ]
            )

            await turn_context.send_activity(MessageFactory.attachment(CardFactory.hero_card(card)))

        elif turn_context.activity.value:
            await self.register_student()
            student_ID = await self.get_student_id()
            await turn_context.send_activity(f"Registration complete. Welcome { self.student_name }! Your student ID is {student_ID}.")
            self.on_register_complete = True
            await self.__send_intro_card(turn_context)

        else:
            await turn_context.send_activity("Please input your name")

    async def __on_submit_activity(self, turn_context: TurnContext):
        if turn_context.activity.value is None:
            await self.__send_submit_card(turn_context)
        elif turn_context.activity.value == 'SUBMIT':
            await self.reset_and_submit()
            await turn_context.send_activity("Your answer has been recorded")
        elif turn_context.activity.value == 'CANCEL':
            await self.switch_on_test_session()
            await self.switch_on_submit_session()
            await self.__send_question_card(turn_context)

    async def __send_question_card(self, turn_context: TurnContext):
        _fetch = self.problem_set[self.counter-1]
        _question = _fetch['desc']
        _question_id = _fetch['id']
        _choices = _fetch['options']
        _button = []
        for _this in _choices:
            _button.append(CardAction(type=ActionTypes.message_back, title=_this['value'], value={'q_id':_question_id, 'ans':_this['key'].upper(), 'msg':f"Answered with '{ _this['value'] }'."}))
        _button.append(CardAction(type=ActionTypes.message_back, title='Back', value={'q_id':None, 'ans':'back'.upper(),'msg':None}))
        _button.append(CardAction(type=ActionTypes.message_back, title='Next', value={'q_id':None, 'ans':'next'.upper(),'msg':None}))
        card = HeroCard(
            title=f"Question '{ self.counter }'.",
            text=_question,
            buttons=_button
        )

        return await turn_context.send_activity(MessageFactory.attachment(CardFactory.hero_card(card)))

    async def __send_submit_card(self, turn_context: TurnContext):
        _keys = sorted(self.answers.keys())
        _text = '|| Student name: '+self.student_name+' '
        for _key in _keys:
            _text += f"|| { _key }. { self.answers[_key]['ans'] } "
        print(_text)
        card = HeroCard(
            title="Here are your test summary: ",
            text=_text,
            buttons=[
                CardAction(type=ActionTypes.message_back, title='Submit', value='submit'.upper()),
                CardAction(type=ActionTypes.message_back, title='Cancel', value='cancel'.upper())
            ]
        )

        return await turn_context.send_activity(MessageFactory.attachment(CardFactory.hero_card(card)))

    async def __send_intro_card(self, turn_context: TurnContext):
        card = HeroCard(
            title=f"Hello { self.student_name }!",
            text="Welcome to the test-taking bot. "
            "To start the test, please reply with the 8-digits test ID "
            "starting with hashtag mark (e.g., #EC2A5FB5). ",
        )

        return await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )