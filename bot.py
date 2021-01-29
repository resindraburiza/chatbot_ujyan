# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

# async lib
import asyncio
import aiohttp

# standard python lib
import os
import json

# bot builder lib
from botbuilder.core import ActivityHandler, TurnContext, CardFactory, MessageFactory, ConversationState, UserState
from botbuilder.core.teams import TeamsActivityHandler
from botbuilder.schema import ChannelAccount, HeroCard, CardImage, CardAction, ActionTypes, ActivityTypes

# state-related lib
from state_management import ConversationData, UserProfile

class MyBot(TeamsActivityHandler):
    def __init__(self, user_state: UserState, conversation_state: ConversationState):
        self.conversation_state = conversation_state
        self.user_state = user_state

        self.conversation_state_accessor = self.conversation_state.create_property("ConversationData")
        self.user_state_accessor = self.user_state.create_property("UserProfile")
        
        self.user_profile = None
        self.conversation_data = None

        # API endpoint
        self.API_base = 'https://ujiyan-webapp.azurewebsites.net/'

    # See https://aka.ms/about-bot-activity-message to learn more about the message and other activity types.

    async def on_turn(self, turn_context: TurnContext):
        await super().on_turn(turn_context)

        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)

    async def reset_and_submit(self):
        # aiohttp session
        session = aiohttp.ClientSession()

        # sumbit
        submit_url = os.path.join(self.API_base,'submissions','create')

        # answer dict creation
        answers = []
        _keys = sorted(self.conversation_data.answers.keys())
        for _key in _keys:
            answers.append({'answer':self.conversation_data.answers[_key]['ans'], 
                'problem_id':self.conversation_data.answers[_key]['q_id']})
    
        params = {'student_id':self.user_profile.student_ID, 'test_id':self.conversation_data.test_ID, 'submissions': answers}
        # print(submit_url)
        # print(params)
        resp = await session.post(submit_url, json=params)
        # print(resp.status)

        await session.close()

        # reset conversation state
        self.conversation_data.problem_set = []
        self.conversation_data.counter = 1
        self.conversation_data.answers = {}
        self.conversation_data.test_ID = ''
        self.conversation_data.test_title = ''
        self.conversation_data.on_test_session = False
        self.conversation_data.on_submit_session = False

    async def asign_test_ID(self, test_id):
        self.conversation_data.test_ID = test_id

    async def switch_on_test_session(self):
        self.conversation_data.on_test_session = ~self.conversation_data.on_test_session

    async def switch_on_submit_session(self):
        self.conversation_data.on_submit_session = ~self.conversation_data.on_submit_session

    async def parse_problem_set(self, json_dump):
        self.conversation_data.test_title = json_dump['title']
        # print(json_dump['problems'])
        self.conversation_data.problem_set.extend(json_dump['problems'])
        # print(self.problem_set)

    async def get_problems(self, problem_id):
        target_path = os.path.join(self.API_base, 'tests', problem_id)
        # target_path = self.API_base
        # print(target_path)

        session = aiohttp.ClientSession()

        async with session.get(target_path) as resp:
            status = resp.status
            # print(status)
            response =  await resp.json()

        await session.close()
        return status, response

    async def register_student(self):
        session = aiohttp.ClientSession()
        path = self.API_base
        path = os.path.join(path,'students')
        async with session.post(path, json={'name':self.user_profile.student_name}) as resp:
            data = await resp.json()
            self.user_profile.student_ID = data['id']
        await session.close()

    async def get_student_id(self):
        return self.user_profile.student_ID

    async def count_up(self):
        self.conversation_data.counter = min(self.conversation_data.counter+1, len(self.conversation_data.problem_set))

    async def count_down(self):
        self.conversation_data.counter = max(self.conversation_data.counter-1, 1)

    async def get_stored_answer(self):
        return self.conversation_data.answers[-1].lower()

    async def update_collected_answer(self, answer, q_id):
        self.conversation_data.answers[str(self.conversation_data.counter)] = {'q_id':q_id, 'ans':answer}
        await self.count_up()

    async def check_collected_answer(self, turn_context: TurnContext):
        if len(self.conversation_data.answers.keys()) == len(self.conversation_data.problem_set):
            # print(self.conversation_data.answers.keys())
            # print(len(self.conversation_data.problem_set))
            await turn_context.send_activity("All questions have been answered. Please type 'submit' for submission.")

    async def on_message_activity(self, turn_context: TurnContext):
        # first and foremost, retreive data from memory state
        self.user_profile = await self.user_state_accessor.get(turn_context, UserProfile)
        # user_profile = await self.user_state_accessor.get(turn_context, UserProfile)
        self.conversation_data = await self.conversation_state_accessor.get(turn_context, ConversationData)
        # conversation_data = await self.conversation_state_accessor.get(turn_context, ConversationData)

        # this is bad code practice with no meaning
        # but I will leave it here
        # await turn_context.send_activity(f"{ turn_context.activity.text }")
        # if turn_context.activity.text is not None:
        #     user_input = turn_context.activity.text
        # else:
        #     user_input = None

        if not self.conversation_data.on_register_complete:
            await self.__send_registration_card(turn_context)

        elif (not self.conversation_data.on_test_session and not self.conversation_data.on_submit_session) and turn_context.activity.text.strip()[:2]!='id':
            # await turn_context.send_activity(f"{ turn_context.activity.text.strip()[:2] }")
            await self.__send_intro_card(turn_context)
        
        # check test ID
        elif (not self.conversation_data.on_test_session and not self.conversation_data.on_submit_session) and turn_context.activity.text.strip()[:2]=='id':
            test_id = turn_context.activity.text.strip()[2:]
            if len(test_id) == 8:
                await turn_context.send_activity("Fetching the requested test id...")
                status, to_parse = await self.get_problems(test_id)
                # await turn_context.send_activity(f"{ status }")
                if status == 404:
                    await turn_context.send_activity(f"Test ID of {test_id} is not found. Please insert the correct test ID.")
                else:
                    await self.asign_test_ID(test_id)
                    await self.parse_problem_set(to_parse)
                    await turn_context.send_activity(f"Test titled {to_parse['title'].capitalize()} is found. There are {len(self.conversation_data.problem_set)} question(s). To submit your answers, type 'submit'. Please type anything to start the test.")
                    await self.switch_on_test_session()
            else:
                await turn_context.send_activity("Test ID should be 8-digits number. Please re-enter the test ID.")
                

        # start test session
        elif self.conversation_data.on_test_session and not self.conversation_data.on_submit_session:
            if turn_context.activity.text is not None:
                if turn_context.activity.text.strip().lower() == 'submit':
                    await self.switch_on_test_session()
                    await self.switch_on_submit_session()
                    await self.__on_submit_activity(turn_context)
                    # await self.conversation_state.save_changes(turn_context)
                    # await self.user_state.save_changes(turn_context)
                    return
                else:
                    await self.__send_question_card(turn_context)
            
            elif turn_context.activity.value is not None:
                _answer = turn_context.activity.value['ans']
                _context = turn_context.activity.value['msg']
                _question_id = turn_context.activity.value['q_id']
                if _answer == 'BACK': 
                    await self.count_down()
                    await turn_context.send_activity("Here is the previous question")
                elif _answer == 'NEXT':
                    await self.count_up()
                    await turn_context.send_activity("Here is the next question")
                else:
                    await turn_context.send_activity(f"Answered with { _context }")
                    await self.update_collected_answer(_answer, _question_id)
                await turn_context.send_activity(f"{len(self.conversation_data.answers.keys())}/{len(self.conversation_data.problem_set)} question(s) have been answered.")
                await self.__send_question_card(turn_context)
            else:
                await self.__send_question_card(turn_context)

            await self.check_collected_answer(turn_context)
        
        # start submission session
        elif not self.conversation_data.on_test_session and self.conversation_data.on_submit_session:
            await self.__on_submit_activity(turn_context)

        # await self.conversation_state.save_changes(turn_context)
        # await self.user_state.save_changes(turn_context)

    async def on_members_added_activity(
        self,
        members_added: ChannelAccount,
        turn_context: TurnContext
    ):
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("Hello and welcome to this test-taking chatbot! Please input your name to register.")

    async def __send_registration_card(self, turn_context: TurnContext):
        # try:
        #     await turn_context.send_activity(f"activit value: {json.loads(turn_context.activity.value)}")
        # except:
        #     pass
        if turn_context.activity.text is not None:
            self.user_profile.student_name = turn_context.activity.text.strip()
            card = HeroCard(
                title="Your name is:",
                text=f"{ self.user_profile.student_name }",
                buttons=[
                    CardAction(type=ActionTypes.message_back, title='Yes', value={'ans': 'True'}),
                    CardAction(type=ActionTypes.message_back, title='No', value={'ans': 'False'})
                ]
            )

            await turn_context.send_activity(MessageFactory.attachment(CardFactory.hero_card(card)))

        elif turn_context.activity.value['ans']=='True':
            await self.register_student()
            student_id = await self.get_student_id()
            await turn_context.send_activity(f"Registration complete. Welcome { self.user_profile.student_name }! Here is your student ID {student_id}.")
            self.conversation_data.on_register_complete = True
            await self.__send_intro_card(turn_context)

        else:
            await turn_context.send_activity("Please input your name")

    async def __on_submit_activity(self, turn_context: TurnContext):
        if turn_context.activity.value is None:
            await self.__send_submit_card(turn_context)
        elif turn_context.activity.value['ans'] == 'SUBMIT':
            await self.reset_and_submit()
            await turn_context.send_activity("Your answer has been recorded.")
        elif turn_context.activity.value['ans'] == 'CANCEL':
            await self.switch_on_test_session()
            await self.switch_on_submit_session()
            await self.__send_question_card(turn_context)
            await self.check_collected_answer(turn_context)

    async def __send_question_card(self, turn_context: TurnContext):
        _fetch = self.conversation_data.problem_set[self.conversation_data.counter-1]
        _question = _fetch['desc']
        _question_id = _fetch['id']
        _choices = _fetch['options']
        _button = []
        for _this in _choices:
            _button.append(CardAction(type=ActionTypes.message_back, title=_this['value'], value={'q_id':_question_id, 'ans':_this['key'].upper(), 'msg':f"Answered with '{ _this['value'] }'."}))
        if self.conversation_data.counter != 1: _button.append(CardAction(type=ActionTypes.message_back, title='Back', value={'q_id':None, 'ans':'back'.upper(),'msg':None}))
        if self.conversation_data.counter != len(self.conversation_data.problem_set): _button.append(CardAction(type=ActionTypes.message_back, title='Next', value={'q_id':None, 'ans':'next'.upper(),'msg':None}))
        card = HeroCard(
            title=f"Question '{ self.conversation_data.counter }'.",
            text=_question,
            buttons=_button
        )

        return await turn_context.send_activity(MessageFactory.attachment(CardFactory.hero_card(card)))

    async def __send_submit_card(self, turn_context: TurnContext):
        _keys = sorted(self.conversation_data.answers.keys())
        _text = ''
        _text = '|| Student name: '+self.user_profile.student_name+' '
        for _key in _keys:
            _text += f"|| { _key }. { self.conversation_data.answers[_key]['ans'] } "
        if len(_keys) < len(self.conversation_data.problem_set):
            _text += '|| There are question(s) you have not answered yet. Do you want to submit anyway?'
        print(_text)
        card = HeroCard(
            title="Here are your test summary: ",
            text=_text,
            buttons=[
                CardAction(type=ActionTypes.message_back, title='Submit', value={'ans':'submit'.upper()}),
                CardAction(type=ActionTypes.message_back, title='Cancel', value={'ans':'cancel'.upper()})
            ]
        )

        return await turn_context.send_activity(MessageFactory.attachment(CardFactory.hero_card(card)))

    async def __send_intro_card(self, turn_context: TurnContext):
        card = HeroCard(
            title=f"Hello { self.user_profile.student_name }!",
            text="Welcome to the test-taking bot. "
            "To start the test, please reply with the 8-digits test ID "
            "starting with 'id' as shown in the example (e.g., id7E4C6B9E). ",
        )

        return await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )