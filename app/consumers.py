import json
from channels.generic.websocket import AsyncWebsocketConsumer

_pending_calls = {}

class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return
        self.room_group_name = f"call_{self.user.username}"
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        username = self.user.username
        if username in _pending_calls:
            for call_data in _pending_calls[username]:
                await self.send(text_data=json.dumps(call_data))
            del _pending_calls[username]

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type")
        target = data.get("target")

        if not target:
            return

        target_group = f"call_{target}"

        if msg_type == "call_offer":
            event = {
                "type": "incoming_call",
                "from": self.user.username,
                "from_name": data.get("from_name", self.user.username),
                "from_avatar": data.get("from_avatar", ""),
                "sdp": data.get("sdp"),
                "is_video": data.get("is_video", True),
                "silent": data.get("silent", False),
            }
            await self.channel_layer.group_send(target_group, event)
            if target not in _pending_calls:
                _pending_calls[target] = []
            _pending_calls[target].append(event)
            if len(_pending_calls[target]) > 3:
                _pending_calls[target] = _pending_calls[target][-3:]

        elif msg_type == "call_answer":
            await self.channel_layer.group_send(
                target_group,
                {
                    "type": "call_answered",
                    "from": self.user.username,
                    "sdp": data.get("sdp"),
                }
            )
            _pending_calls.pop(target, None)

        elif msg_type == "ice_candidate":
            await self.channel_layer.group_send(
                target_group,
                {
                    "type": "ice_candidate",
                    "from": self.user.username,
                    "candidate": data.get("candidate"),
                }
            )

        elif msg_type == "call_end":
            _pending_calls.pop(target, None)
            _pending_calls.pop(self.user.username, None)
            await self.channel_layer.group_send(
                target_group,
                {
                    "type": "call_ended",
                    "from": self.user.username,
                }
            )

        elif msg_type == "call_reject":
            _pending_calls.pop(target, None)
            await self.channel_layer.group_send(
                target_group,
                {
                    "type": "call_rejected",
                    "from": self.user.username,
                }
            )

        elif msg_type == "call_offer_renegotiate":
            await self.channel_layer.group_send(
                target_group,
                {
                    "type": "call_offer_renegotiate",
                    "from": self.user.username,
                    "sdp": data.get("sdp"),
                }
            )

        elif msg_type == "call_answer_renegotiate":
            await self.channel_layer.group_send(
                target_group,
                {
                    "type": "call_answer_renegotiate",
                    "from": self.user.username,
                    "sdp": data.get("sdp"),
                }
            )

        elif msg_type == "call_busy":
            await self.channel_layer.group_send(
                target_group,
                {
                    "type": "call_busy",
                    "from": self.user.username,
                }
            )

    async def incoming_call(self, event):
        await self.send(text_data=json.dumps({
            "type": "incoming_call",
            "from": event["from"],
            "from_name": event.get("from_name", event["from"]),
            "from_avatar": event.get("from_avatar", ""),
            "sdp": event["sdp"],
            "is_video": event["is_video"],
            "silent": event["silent"],
        }))

    async def call_answered(self, event):
        await self.send(text_data=json.dumps({
            "type": "call_answered",
            "from": event["from"],
            "sdp": event["sdp"],
        }))

    async def ice_candidate(self, event):
        await self.send(text_data=json.dumps({
            "type": "ice_candidate",
            "from": event["from"],
            "candidate": event["candidate"],
        }))

    async def call_ended(self, event):
        await self.send(text_data=json.dumps({
            "type": "call_ended",
            "from": event["from"],
        }))

    async def call_rejected(self, event):
        await self.send(text_data=json.dumps({
            "type": "call_rejected",
            "from": event["from"],
        }))

    async def call_busy(self, event):
        await self.send(text_data=json.dumps({
            "type": "call_busy",
            "from": event["from"],
        }))

    async def call_offer_renegotiate(self, event):
        await self.send(text_data=json.dumps({
            "type": "call_offer_renegotiate",
            "from": event["from"],
            "sdp": event["sdp"],
        }))

    async def call_answer_renegotiate(self, event):
        await self.send(text_data=json.dumps({
            "type": "call_answer_renegotiate",
            "from": event["from"],
            "sdp": event["sdp"],
        }))
