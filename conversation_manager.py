# conversation_manager.py
from collections import deque
from config import CONVERSATION_BUFFER_SIZE


class ConversationManager:
    """대화 관리를 담당하는 클래스"""

    def __init__(self, llm_utils):
        self.llm_utils = llm_utils
        self.conversation_buffer = deque(maxlen=CONVERSATION_BUFFER_SIZE)
        self.conversation_summary = "아직 대화를 시작하지 않았다."

    def add_message(self, speaker: str, message: str):
        """대화 메시지 추가"""
        self.conversation_buffer.append((speaker, message))

    def summarize_conversation(self):
        """현재 대화를 요약 (플레이어의 마지막 발언을 최우선으로)"""
        print("DEBUG (Context): 현재 대화 맥락을 요약합니다...")

        if not self.conversation_buffer:
            return

        buffer_str = "\n".join([f"{spk}: {txt}" for spk, txt in self.conversation_buffer])

        # --- 여기를 수정했습니다 ---
        # 플레이어의 마지막 발언을 명시적으로 분리하여 중요도를 높입니다.
        last_speaker, last_message = self.conversation_buffer[-1]

        # 플레이어의 마지막 발언이 무엇인지 명확히 전달합니다.
        if last_speaker == "Player":
            last_player_input = f'플레이어가 방금 "{last_message}" 라고 말했다.'
        else:
            last_player_input = "가장 최근 대화는 NPC의 응답이었다."

        prompt = (
            "너는 대화의 핵심을 파악하는 AI야. 아래 대화 기록을 바탕으로, NPC가 다음 행동을 결정하는 데 가장 중요한 '현재 상황'을 한 문장으로 요약해줘.\n\n"
            "### 가장 중요한 규칙 ###\n"
            "1. 플레이어의 '요구', '질문', '명령', '강한 감정 표현'이 대화의 최우선 순위야.\n"
            "2. 이전 대화 주제보다 플레이어의 가장 마지막 발언에 담긴 의도를 해결하는 것이 훨씬 더 중요해.\n\n"
            f"### 최근 대화 기록 ###\n{buffer_str}\n\n"
            f"### 현재 가장 중요한 사실 ###\n{last_player_input}\n\n"
            "### 현재 상황 요약 (한 문장으로):"
        )
        summary = self.llm_utils.get_llm_response(prompt, temperature=0.3, max_tokens=100)
        self.conversation_summary = summary
        print(f"DEBUG (Context): 요약된 현재 대화 맥락 -> {self.conversation_summary}")

    def get_conversation_summary(self) -> str:
        """대화 요약 반환"""
        return self.conversation_summary

    def clear_buffer(self):
        """대화 버퍼 초기화"""
        self.conversation_buffer.clear()
        self.conversation_summary = "아직 대화를 시작하지 않았다."