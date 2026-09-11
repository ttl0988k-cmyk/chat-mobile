# patch_connector.py
import re

file_path = r"C:\daon\cafe\LLM\chat\connector\daon_remote_connector.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update DeltaStreamManager.add_token and add cancel()
old_add_token = '''    def add_token(self, conv_id: str, user_id: str, stream_id: str, text: str):











        with self.lock:











            first_token = conv_id not in self.buffers











            if first_token:











                # [v3] 새 응답 시작 — 이전 응답의 row를 재사용하지 않음











                self.msg_ids.pop(conv_id, None)











            self.buffers[conv_id] = self.buffers.get(conv_id, '') + text'''

new_add_token = '''    def add_token(self, conv_id: str, user_id: str, stream_id: str, text: str):
        with self.lock:
            prev_stream = self.stream_ids.get(conv_id)
            if prev_stream is not None and prev_stream != stream_id:
                log.info('🔄 새 스트림 감지 (이전=%s, 현재=%s) — 이전 버퍼 및 msg_id 초기화',
                         prev_stream[:8] if prev_stream else 'None', stream_id[:8] if stream_id else 'None')
                self.buffers.pop(conv_id, None)
                self.msg_ids.pop(conv_id, None)
                self.last_flush.pop(conv_id, None)

            first_token = conv_id not in self.buffers
            if first_token:
                # [v3] 새 응답 시작 — 이전 응답의 row를 재사용하지 않음
                self.msg_ids.pop(conv_id, None)
            self.buffers[conv_id] = self.buffers.get(conv_id, '') + text'''

if old_add_token in content:
    content = content.replace(old_add_token, new_add_token, 1)
    print("1. add_token replaced successfully")
else:
    print("WARNING: old_add_token not found by exact string, trying regex/normalized search")

# 2. Add cancel() to DeltaStreamManager after finish()
old_finish = '''            self.msg_ids.pop(conv_id, None)  # [v3] 다음 응답은 반드시 새 row'''

new_finish = '''            self.msg_ids.pop(conv_id, None)  # [v3] 다음 응답은 반드시 새 row

    def cancel(self, conv_id: str):
        """스트림 취소 시 버퍼와 msg_id를 즉시 완전 삭제하여 다음 응답이 이전 row에 덮어써지지 않도록 보장."""
        with self.lock:
            log.info('🧹 DeltaStreamManager.cancel 호출 — conv=%s', (conv_id or '')[:8])
            self.buffers.pop(conv_id, None)
            self.last_flush.pop(conv_id, None)
            self.user_ids.pop(conv_id, None)
            self.stream_ids.pop(conv_id, None)
            self.msg_ids.pop(conv_id, None)'''

if old_finish in content:
    content = content.replace(old_finish, new_finish, 1)
    print("2. cancel() added successfully")
else:
    print("WARNING: old_finish not found")

# 3. In handle_user_message (mtype == 'interrupt'): add _delta_mgr.cancel(conv_id)
old_interrupt = '''        _status_mgr.clear(conv_id)

        _CONV_STREAMS.pop(conv_id, None)'''

new_interrupt = '''        _status_mgr.clear(conv_id)
        _delta_mgr.cancel(conv_id)
        _CONV_STREAMS.pop(conv_id, None)'''

if old_interrupt in content:
    content = content.replace(old_interrupt, new_interrupt, 1)
    print("3. interrupt handler updated with _delta_mgr.cancel")
else:
    print("WARNING: old_interrupt not found")

# 4. In on_event: add stale stream check at top
old_on_event = '''    def on_event(event, data):











        if event == 'token':'''

new_on_event = '''    def on_event(event, data):
        # 만약 이 스트림이 이미 취소되었거나 다른 새 스트림으로 교체되었다면 오래된 이벤트는 즉시 무시
        if _CONV_STREAMS.get(conv_id) != stream_id:
            return False

        if event == 'token':'''

if old_on_event in content:
    content = content.replace(old_on_event, new_on_event, 1)
    print("4. on_event stale stream guard added")
else:
    print("WARNING: old_on_event not found")

# 5. In on_event (event == 'cancel'): add _delta_mgr.cancel(conv_id)
old_cancel_event = '''        elif event == 'cancel':











            _status_mgr.clear(conv_id)  # [v3] 상태 배지 제거'''

new_cancel_event = '''        elif event == 'cancel':
            _status_mgr.clear(conv_id)  # [v3] 상태 배지 제거
            _delta_mgr.cancel(conv_id)   # [중요] 이전 스트림 버퍼와 msg_id 완전 초기화
            if _CONV_STREAMS.get(conv_id) == stream_id:
                _CONV_STREAMS.pop(conv_id, None)'''

if old_cancel_event in content:
    content = content.replace(old_cancel_event, new_cancel_event, 1)
    print("5. cancel event handler updated with _delta_mgr.cancel")
else:
    print("WARNING: old_cancel_event not found")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Finished patching connector!")
