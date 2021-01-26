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
        self.on_test_session = False
        self.on_submit_session = False
        self.session = aiohttp.ClientSession()

        # API endpoint
        # self.API_base = 'https://virtserver.swaggerhub.com/AgentOfChange/ninemillion/1.0.0'
        self.API_base = 'https://gist.githubusercontent.com/wawando/3073a175b3111cb966670497e6a951cf/raw/b8e968077a40c3344f4c99442a1b3a4689941e06/'
        self.API_submit = 'https://virtserver.swaggerhub.com/AgentOfChange/ninemillion/1.0.0/submissions'

    # See https://aka.ms/about-bot-activity-message to learn more about the message and other activity types.

    async def reset_and_submit(self):
        # sumbit
        print(self.answers)
        params = {'student_id':self.student_ID, 'problem_id':self.test_ID, 'answer':json.dumps(self.answers)}
        await self.session.post(self.API_submit, params=params)
        # reset
        self.problem_set = []
        self.counter = 1
        self.answers = {}
        self.student_ID = ''
        self.student_name = ''
        self.test_ID = ''
        self.on_test_session = False
        self.on_submit_session = False

    async def asign_test_ID(self, test_id):
        self.test_ID = test_id

    async def switch_on_test_session(self):
        self.on_test_session = ~self.on_test_session

    async def switch_on_submit_session(self):
        self.on_submit_session = ~self.on_submit_session

    async def parse_problem_set(self, json_dump):
        self.problem_set.append(json.loads(json_dump))
        print(self.problem_set)

    async def get_problems(self, problem_id):
        # target_path = os.path.join(self.API_base, 'problems', problem_id)
        target_path = self.API_base
        print(target_path)
        async with self.session.get(target_path) as resp:
            status = resp.status
            response =  await resp.text()        
        return status, response

    async def count_up(self):
        self.counter = min(self.counter+1, len(self.problem_set))

    async def count_down(self):
        self.counter = max(self.counter-1, 1)

    async def get_stored_answer(self):
        return self.answers[-1].lower()

    async def update_collected_answer(self, answer):
        self.answers[str(self.counter)] = str(answer)
        await self.count_up()

    async def on_message_activity(self, turn_context: TurnContext):
        if (turn_context.activity.text is not None):
            user_input = turn_context.activity.text.lower()

        if (not self.on_test_session and not self.on_submit_session) and user_input[0]!='#':
            await self.__send_intro_card(turn_context)
        
        # check test ID
        elif (not self.on_test_session and not self.on_submit_session) and user_input[0]=='#':
            test_id = user_input[1:]
            if len(test_id) != 6: 
                await turn_context.send_activity("Test ID should be 6-digits number")
            else:
                status, to_parse = await self.get_problems(test_id)
                if status == 404: 
                    await turn_context.send_activity("Test ID is not found. Please insert the correct test ID")
                else:
                    await turn_context.send_activity("Test ID found. Type anything to start the test.")
                    await self.asign_test_ID(test_id)
                    await self.parse_problem_set(to_parse)
                    await self.switch_on_test_session()
        
        # start test session
        elif self.on_test_session and not self.on_submit_session:
            if turn_context.activity.text is not None:
                if turn_context.activity.text.lower() == 'submit':
                    await self.switch_on_test_session()
                    await self.switch_on_submit_session()
                    await turn_context.send_activity("Please insert your student ID")
                else:
                    await self.__send_question_card(turn_context)
            elif turn_context.activity.value is not None:
                _answer = turn_context.activity.value['ans']
                _context = turn_context.activity.value['msg']
                if _answer == 'BACK': 
                    await self.count_down()
                    await turn_context.send_activity("Go back one question")
                elif _answer == 'NEXT':
                    await self.count_up()
                    await turn_context.send_activity("Go forward one question")
                else:
                    await turn_context.send_activity(f"Answered with { _context }")
                    await self.update_collected_answer(_answer)
                await self.__send_question_card(turn_context)
            else:
                await self.__send_question_card(turn_context)
            # feed question
            # wait response
        
        elif not self.on_test_session and self.on_submit_session:
            await self.__on_submit_activity(turn_context)

        # response = await self.get_problems('E62C26')
        # counter = await self.count_up()
        # await self.store_answer(turn_context.activity.text)
        # latest_answer = await self.get_stored_answer()
        # await turn_context.send_activity(f"Test get '{ response }'")
        # await turn_context.send_activity(f"You said '{ turn_context.activity.text }'")
        # await turn_context.send_activity("Counter now is {}".format(counter))
        # await turn_context.send_activity("Your latest answer is: {}".format(latest_answer))

    async def on_members_added_activity(
        self,
        members_added: ChannelAccount,
        turn_context: TurnContext
    ):
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("Hello and welcome to this test-taking chatbot!")

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
        _choices = _fetch['options']
        _button = []
        for _this in _choices:
            _button.append(CardAction(type=ActionTypes.message_back, title=_this['value'], value={'ans':_this['key'].upper(),'msg':f"Answered with '{ _this['value'] }'."}))
        _button.append(CardAction(type=ActionTypes.message_back, title='Back', value={'ans':'back'.upper(),'msg':None}))
        _button.append(CardAction(type=ActionTypes.message_back, title='Next', value={'ans':'next'.upper(),'msg':None}))
        card = HeroCard(
            title=f"Question '{ self.counter }'.",
            text=_question,
            buttons=_button
        )

        return await turn_context.send_activity(MessageFactory.attachment(CardFactory.hero_card(card)))

    async def __send_submit_card(self, turn_context: TurnContext):
        _keys = sorted(self.answers.keys())
        self.student_ID = turn_context.activity.text
        _text = '|| '+self.student_ID+' '
        for _key in _keys:
            _text += f"|| { _key }. { self.answers[_key] } "
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
            title="Hello student!",
            text="Welcome to the text-taking bot. "
            "To start the test, please reply with the 6-digits test ID "
            "starting with hashtag mark (e.g., #ER227D). ",
        )

        return await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )