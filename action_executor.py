# action_executor.py - LLM 기반 완전 개선 버전
import random


class ActionExecutor:
    """NPC의 행동 실행을 담당하는 클래스 (LLM 기반 장소 결정)"""

    def __init__(self, npc_agent, llm_utils):
        self.npc = npc_agent
        self.llm_utils = llm_utils

        # 행동 상태
        self.current_action = None
        self.action_start_time = None
        self.action_duration = 0
        self.target_location = None
        self.action_description = ""
        self.action_emoji = "🤔"

        # Unity에서 제공받은 사용 가능한 장소 목록
        self.available_locations = []

    def set_available_locations(self, locations: list):
        """Unity 환경에서 사용 가능한 장소 목록을 설정"""
        self.available_locations = locations
        print(f"[ActionExecutor] 사용 가능한 장소 목록 업데이트: {self.available_locations}")

    def _determine_location_with_llm(self, action, activity_context=""):
        """LLM을 사용하여 행동에 맞는 최적의 장소 결정"""
        if not self.available_locations:
            print("[ActionExecutor] 경고: 사용 가능한 장소 목록이 비어있습니다.")
            return "대학교:중앙광장"  # 기본 장소

        # 장소 목록을 문자열로 변환
        locations_str = "\n".join([f"- {loc}" for loc in self.available_locations])

        prompt = f"""
        다음은 NPC {self.npc.name}의 정보입니다:
        - 성격: {self.npc.persona}
        - 현재 상황: {activity_context}

        NPC가 "{action}"라는 행동을 하려고 합니다.

        다음 장소 목록 중에서 이 행동을 하기에 가장 적절한 장소를 하나만 선택해주세요:
        {locations_str}

        선택 기준:
        1. 행동의 특성에 맞는 장소인가?
        2. NPC의 성격과 상황에 어울리는가?
        3. 해당 장소에서 그 행동을 하는 것이 자연스러운가?

        응답 형식:
        장소: [선택한 장소]
        이유: [선택 이유를 한 줄로]

        예시:
        장소: 도서관:열람실
        이유: 조용한 환경에서 집중해서 자료를 찾기에 적합함
        """

        try:
            response = self.llm_utils.get_llm_response(
                prompt, temperature=0.3, max_tokens=150
            )

            # 응답에서 장소 추출
            lines = response.strip().split('\n')
            selected_location = None
            reason = ""

            for line in lines:
                if line.startswith("장소:"):
                    location_text = line.replace("장소:", "").strip()
                    # 정확한 매칭을 위해 사용 가능한 장소 목록에서 찾기
                    for available_loc in self.available_locations:
                        if available_loc in location_text or location_text in available_loc:
                            selected_location = available_loc
                            break
                elif line.startswith("이유:"):
                    reason = line.replace("이유:", "").strip()

            if selected_location:
                print(f"[ActionExecutor] LLM이 선택한 장소: {selected_location} (이유: {reason})")
                return selected_location
            else:
                print(f"[ActionExecutor] LLM 응답에서 유효한 장소를 찾을 수 없음: {response}")
                return self.available_locations[0]  # 첫 번째 장소를 기본값으로

        except Exception as e:
            print(f"[ActionExecutor] 장소 결정 중 오류 발생: {e}")
            return self.available_locations[0] if self.available_locations else "대학교:중앙광장"

    def _decompose_activity_with_llm(self, activity, duration):
        """LLM을 사용하여 활동을 구체적인 행동으로 분해"""
        prompt = f"""
        {self.npc.name}({self.npc.persona})가 "{activity}"라는 활동을 {duration}분 동안 할 예정입니다.

        이 활동을 더 구체적이고 자연스러운 행동 하나로 표현해주세요.

        조건:
        1. NPC의 성격을 반영할 것
        2. 실제로 그 시간 동안 할 수 있는 현실적인 행동일 것
        3. 간단하고 명확한 표현일 것 (5단어 이내)

        예시:
        활동: "공부" → 행동: "수학 문제 풀기"
        활동: "휴식" → 행동: "음악 들으며 쉬기"
        활동: "졸업 작품 구상" → 행동: "아이디어 스케치하기"

        응답 형식:
        행동: [구체적인 행동]
        """

        try:
            response = self.llm_utils.get_llm_response(
                prompt, temperature=0.4, max_tokens=50
            )

            # 응답에서 행동 추출
            for line in response.strip().split('\n'):
                if line.startswith("행동:"):
                    detailed_action = line.replace("행동:", "").strip()
                    print(f"[ActionExecutor] LLM이 분해한 행동: '{activity}' → '{detailed_action}'")
                    return detailed_action

            # 응답 형식이 다르면 전체 응답을 행동으로 사용
            cleaned_response = response.strip().replace("행동:", "").strip()
            return cleaned_response if cleaned_response else activity

        except Exception as e:
            print(f"[ActionExecutor] 행동 분해 중 오류 발생: {e}")
            return activity

    def _generate_contextual_action_description(self, action, location, activity_context):
        """맥락을 고려한 행동 설명과 이모지 생성"""
        prompt = f"""
        {self.npc.name}({self.npc.persona})가 현재 상황에서 행동하고 있습니다.

        현재 상황:
        - 장소: {location}
        - 행동: {action}
        - 맥락: {activity_context}

        이 상황을 자연스럽고 생생하게 표현하는 한 문장과 적절한 이모지를 만들어주세요.

        응답 형식:
        설명: [행동을 생생하게 묘사하는 한 문장]
        이모지: [상황에 맞는 이모지 하나]

        예시:
        설명: 도서관 열람실에서 졸업 작품 아이디어를 스케치북에 그려가며 구상하고 있다
        이모지: ✏️

        주의사항:
        - NPC의 성격을 반영할 것
        - 장소와 행동이 자연스럽게 어우러지도록 할 것
        - 현재 진행형으로 표현할 것
        """

        try:
            response = self.llm_utils.get_llm_response(
                prompt, temperature=0.5, max_tokens=100
            )

            lines = response.strip().split('\n')
            description = f"{location}에서 {action}"  # 기본값
            emoji = "🤔"  # 기본값

            for line in lines:
                if line.startswith("설명:"):
                    description = line.replace("설명:", "").strip()
                elif line.startswith("이모지:"):
                    emoji = line.replace("이모지:", "").strip()

            print(f"[ActionExecutor] LLM이 생성한 설명: {emoji} {description}")
            return description, emoji

        except Exception as e:
            print(f"[ActionExecutor] 행동 설명 생성 중 오류 발생: {e}")
            return f"{location}에서 {action}", "🤔"

    def determine_next_action(self, current_time, planner):
        """다음 행동 결정 (LLM 기반으로 개선)"""
        print(f"[ActionExecutor] {self.npc.name}의 다음 행동 결정 중... (현재 시간: {current_time.strftime('%H:%M')})")

        # 1. 현재 활동이 끝났는지 확인
        if self._is_current_action_finished(current_time):
            # 2. 플래너에서 현재 시간의 활동 가져오기
            activity, duration = planner.get_current_activity(current_time)
            activity_context = f"오늘의 주요 계획 중 하나인 {activity}을 {duration}분간 수행"

            print(f"[ActionExecutor] 플래너에서 받은 활동: '{activity}' ({duration}분)")

            # 3. LLM을 사용해 활동을 구체적인 행동으로 분해
            detailed_action = self._decompose_activity_with_llm(activity, duration)

            # 4. LLM을 사용해 행동에 맞는 위치 결정
            target_location = self._determine_location_with_llm(detailed_action, activity_context)

            # 5. LLM을 사용해 맥락적 행동 설명과 이모지 생성
            description, emoji = self._generate_contextual_action_description(
                detailed_action, target_location, activity_context
            )

            # 6. 새로운 행동 설정
            self._set_new_action(
                action=detailed_action,
                location=target_location,
                description=description,
                emoji=emoji,
                duration=duration,
                start_time=current_time
            )

            return True  # 새로운 행동 설정됨

        return False  # 기존 행동 계속

    def _is_current_action_finished(self, current_time):
        """현재 행동이 끝났는지 확인"""
        if not self.current_action or not self.action_start_time:
            print(f"[ActionExecutor] 현재 행동 없음 -> 새 행동 필요")
            return True

        elapsed_minutes = (current_time - self.action_start_time).total_seconds() / 60
        finished = elapsed_minutes >= self.action_duration

        print(f"[ActionExecutor] 행동 진행상황: {elapsed_minutes:.1f}/{self.action_duration}분 (완료: {finished})")

        return finished

    def _decompose_activity(self, activity, duration):
        """활동을 구체적인 행동으로 분해 (기존 메서드, 호환성 유지)"""
        # LLM 버전을 우선 사용하되, 실패 시 기존 로직 사용
        try:
            return self._decompose_activity_with_llm(activity, duration)
        except:
            print("[ActionExecutor] LLM 분해 실패, 기존 로직 사용")
            # 기존 하드코딩 로직을 백업으로 유지
            if "공부" in activity or "과제" in activity:
                actions = ["자료 찾기", "읽기", "정리하기", "문제 풀기"]
                return random.choice(actions)
            elif "휴식" in activity:
                actions = ["음악 듣기", "폰 보기", "멍때리기", "간식 먹기"]
                return random.choice(actions)
            elif "식사" in activity:
                actions = ["메뉴 고르기", "주문하기", "식사하기", "정리하기"]
                return random.choice(actions)
            else:
                return activity

    def _determine_location(self, action):
        """행동에 맞는 위치 결정 (기존 메서드, 호환성 유지)"""
        # LLM 버전을 우선 사용하되, 실패 시 기존 로직 사용
        try:
            return self._determine_location_with_llm(action)
        except:
            print("[ActionExecutor] LLM 장소 결정 실패, 기본 장소 사용")
            # 기존 하드코딩 매핑을 백업으로 유지
            activity_locations = {
                "잠자기": "집:침실",
                "기상": "집:침실",
                "아침 루틴": "집:화장실",
                "아침식사": "집:부엌",
                "점심식사": "카페:식당",
                "저녁식사": "집:부엌",
                "공부": "도서관:열람실",
                "과제": "도서관:열람실",
                "수업": "대학교:강의실",
                "휴식": "카페:휴게실",
                "개인시간": "집:거실",
                "취미활동": "집:거실",
                "운동": "체육관:운동실",
                "쇼핑": "상점:매장",
                "산책": "공원:산책로"
            }

            for activity_key, location in activity_locations.items():
                if activity_key in action:
                    return location

            return "대학교:중앙광장"

    def _generate_action_description(self, action, location):
        """행동 설명과 이모지 생성 (기존 메서드, 호환성 유지)"""
        # LLM 버전을 우선 사용하되, 실패 시 기존 로직 사용
        try:
            return self._generate_contextual_action_description(action, location, "")
        except:
            print("[ActionExecutor] LLM 설명 생성 실패, 기존 로직 사용")
            # 기존 LLM 호출 로직 유지
            prompt = f"""
            {self.npc.name}({self.npc.persona})가 {location}에서 "{action}"를 하고 있습니다.

            1. 이 상황을 자연스럽게 설명하는 한 문장을 만들어주세요.
            2. 이 행동을 나타내는 적절한 이모지 하나를 골라주세요.

            형식:
            설명: [행동 설명]
            이모지: [이모지]

            예시:
            설명: 도서관에서 과제 자료를 찾고 있다
            이모지: 📚
            """

            try:
                response = self.llm_utils.get_llm_response(
                    prompt, temperature=0.3, max_tokens=100
                )

                lines = response.strip().split('\n')
                description = action  # 기본값
                emoji = "🤔"  # 기본값

                for line in lines:
                    if line.startswith("설명:"):
                        description = line.replace("설명:", "").strip()
                    elif line.startswith("이모지:"):
                        emoji = line.replace("이모지:", "").strip()

                return description, emoji

            except Exception as e:
                print(f"[ActionExecutor] 행동 설명 생성 실패: {e}")
                return f"{location}에서 {action}", "🤔"

    def _set_new_action(self, action, location, description, emoji, duration, start_time):
        """새로운 행동 설정"""
        self.current_action = action
        self.target_location = location
        self.action_description = description
        self.action_emoji = emoji
        self.action_duration = duration
        self.action_start_time = start_time

        print(f"[ActionExecutor] 새로운 행동: {emoji} {description} (@{location}, {duration}분)")

        # 메모리에 행동 기록
        self.npc.memory_manager.add_memory(
            'event',
            f"{self.npc.name}가 {location}에서 {action}를 시작했다",
            importance=5
        )

        # 현재 상황을 생각으로 기록
        self.npc.memory_manager.add_memory(
            'thought',
            f"지금 {location}에서 {action}를 하고 있다.",
            importance=4
        )

    def get_current_status(self):
        """현재 행동 상태 반환"""
        if not self.current_action:
            return {
                "action": "대기 중",
                "description": "할 일을 찾고 있음",
                "emoji": "🤔",
                "location": "알 수 없음",
                "progress": 0.0
            }

        # 진행률 계산
        if self.action_start_time and self.action_duration > 0:
            from time_manager import time_manager
            current_time = time_manager.get_current_time()
            elapsed_minutes = (current_time - self.action_start_time).total_seconds() / 60
            progress = min(1.0, elapsed_minutes / self.action_duration)
        else:
            progress = 0.0

        return {
            "action": self.current_action,
            "description": self.action_description,
            "emoji": self.action_emoji,
            "location": self.target_location,
            "progress": progress,
            "remaining_minutes": max(0, self.action_duration - elapsed_minutes) if self.action_start_time else 0
        }

    def handle_player_interaction(self, player_location, interaction_type="chat"):
        """플레이어 상호작용 처리"""
        print(f"[ActionExecutor] 플레이어 상호작용 처리: {interaction_type}")

        # 상호작용으로 인한 감정 변화
        self.npc.update_emotion("호기심")

        # 현재 행동 일시 중단
        if self.current_action:
            self.npc.memory_manager.add_memory(
                'event',
                f"플레이어와 {interaction_type} 상호작용으로 {self.current_action}를 중단했다",
                importance=7
            )

        # 대화 모드로 전환
        self._set_new_action(
            action="플레이어와 대화",
            location=player_location,
            description="플레이어와 대화 중",
            emoji="💬",
            duration=10,  # 기본 10분
            start_time=None  # 대화는 시간 제한 없음
        )

        return True

    def get_unity_movement_command(self):
        """Unity에 보낼 이동 명령 생성"""
        if not self.target_location:
            return None

        # LLM을 사용해 이동 스타일 결정
        movement_style = self._determine_movement_style()

        return {
            "npc_id": self.npc.name,
            "target_location": self.target_location,
            "action_description": self.action_description,
            "emoji": self.action_emoji,
            "movement_style": movement_style
        }

    def _determine_movement_style(self):
        """LLM을 사용해 이동 스타일 결정"""
        prompt = f"""
        {self.npc.name}({self.npc.persona})가 "{self.current_action}"를 하기 위해 {self.target_location}로 이동하려고 합니다.

        NPC의 성격과 현재 상황을 고려하여 적절한 이동 스타일을 선택해주세요:
        - fast: 급하게, 빨리
        - normal: 보통 속도로
        - slow: 천천히, 여유롭게

        응답: [fast/normal/slow 중 하나만]
        """

        try:
            response = self.llm_utils.get_llm_response(
                prompt, temperature=0.3, max_tokens=10
            ).strip().lower()

            if response in ["fast", "normal", "slow"]:
                return response
            else:
                return "normal"

        except Exception as e:
            print(f"[ActionExecutor] 이동 스타일 결정 중 오류: {e}")
            return "normal"

    def _location_to_coordinates(self, location):
        """위치 문자열을 Unity 좌표로 변환 (기존 메서드 유지)"""
        # 임시 좌표 매핑 (실제로는 Unity의 위치 시스템과 연동)
        coordinates_map = {
            "집:침실": {"x": 10, "z": 10},
            "집:부엌": {"x": 15, "z": 10},
            "집:거실": {"x": 12, "z": 8},
            "도서관:열람실": {"x": 50, "z": 30},
            "카페:휴게실": {"x": 30, "z": 20},
            "대학교:강의실": {"x": 70, "z": 40},
            "대학교:중앙광장": {"x": 60, "z": 35}
        }

        return coordinates_map.get(location, {"x": 0, "z": 0})

    def _get_movement_speed(self):
        """이동 속도 결정 (기존 메서드, 호환성 유지)"""
        if "급하" in self.action_description or "서둘" in self.action_description:
            return "fast"
        elif "천천히" in self.action_description or "여유" in self.action_description:
            return "slow"
        else:
            return "normal"