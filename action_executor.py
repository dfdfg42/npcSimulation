# action_executor.py - 논문 스타일 Task Decomposition 적용 버전
import random


class ActionExecutor:
    """NPC의 행동 실행을 담당하는 클래스 (논문 스타일 Task Decomposition 적용)"""

    def __init__(self, npc_agent, llm_utils):
        self.npc = npc_agent
        self.llm_utils = llm_utils

        # 행동 상태
        self.current_action_sequence = []  # 분해된 세부 행동들
        self.current_step_index = 0  # 현재 실행 중인 세부 행동 인덱스
        self.action_start_time = None
        self.total_duration = 0
        self.target_location = None
        self.main_activity = ""

        # Unity에서 제공받은 사용 가능한 장소 목록
        self.available_locations = []

    def set_available_locations(self, locations: list):
        """Unity 환경에서 사용 가능한 장소 목록을 설정"""
        self.available_locations = locations
        print(f"[ActionExecutor] 사용 가능한 장소 목록 업데이트: {self.available_locations}")

    def _decompose_task_with_llm(self, activity, duration):
        """논문 스타일: 활동을 여러 세부 작업으로 분해"""
        locations_str = ", ".join(self.available_locations) if self.available_locations else "대학교:중앙광장"

        prompt = f"""
        {self.npc.name}({self.npc.persona})가 "{activity}"라는 활동을 {duration}분 동안 할 예정입니다.

        이 활동을 시간 순서대로 여러 개의 세부 작업으로 분해해주세요.
        각 세부 작업은 실제로 그 시간 동안 할 수 있는 현실적인 행동이어야 합니다.

        ### 분해 원칙 ###
        1. NPC의 성격과 전공을 반영할 것
        2. 시간 순서에 따라 논리적으로 배열할 것
        3. 각 세부 작업의 시간은 5~30분 사이로 할 것
        4. 모든 세부 작업 시간의 합이 {duration}분이 되도록 할 것
        5. 각 작업은 다음 장소 중 하나에서 수행 가능해야 함: {locations_str}

        ### 분해 예시 ###
        활동: "아침 루틴 (60분)"
        1. 화장실 가기, 5분, 집:화장실
        2. 세수하기, 10분, 집:화장실
        3. 옷 갈아입기, 15분, 집:침실
        4. 머리 정리하기, 10분, 집:침실
        5. 가방 챙기기, 10분, 집:침실
        6. 현관에서 신발 신기, 5분, 집:현관
        7. 집 나서기, 5분, 집:현관

        활동: "공부 (120분)"
        1. 도서관 자리 찾기, 10분, 도서관:열람실
        2. 자료 준비하기, 15분, 도서관:열람실
        3. 수학 문제 풀기, 45분, 도서관:열람실
        4. 휴식 시간, 10분, 도서관:휴게실
        5. 영어 단어 암기, 40분, 도서관:열람실

        ### 응답 형식 ###
        각 줄을 다음 형식으로 작성해주세요:
        순번. 세부작업명, 소요시간, 장소

        예: 1. 화장실 가기, 5, 집:화장실
        """

        try:
            response = self.llm_utils.get_llm_response(
                prompt, temperature=0.3, max_tokens=400
            )

            print(f"[ActionExecutor] LLM 분해 응답: {response}")

            # 응답 파싱
            task_sequence = []
            total_parsed_time = 0

            lines = response.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line or not any(char.isdigit() for char in line):
                    continue

                # "순번. 작업명, 시간, 장소" 형식 파싱
                try:
                    # 첫 번째 점 이후 부분 추출
                    if '.' in line:
                        content = line.split('.', 1)[1].strip()
                    else:
                        content = line

                    # 쉼표로 분리
                    parts = [p.strip() for p in content.split(',')]
                    if len(parts) >= 3:
                        task_name = parts[0]
                        duration_str = ''.join(filter(str.isdigit, parts[1]))
                        location = parts[2]

                        if duration_str:
                            task_duration = int(duration_str)
                            # 장소가 사용 가능한 장소 목록에 있는지 확인
                            if location in self.available_locations or not self.available_locations:
                                task_sequence.append({
                                    'task': task_name,
                                    'duration': task_duration,
                                    'location': location
                                })
                                total_parsed_time += task_duration
                                print(f"[ActionExecutor] 세부 작업 추가: {task_name} ({task_duration}분) @ {location}")

                except (ValueError, IndexError) as e:
                    print(f"[ActionExecutor] 파싱 오류: {line} - {e}")
                    continue

            # 시간 조정
            if task_sequence:
                # 시간이 부족하거나 초과하면 조정
                time_diff = duration - total_parsed_time
                if abs(time_diff) > 5:  # 5분 이상 차이나면 조정
                    self._adjust_task_timing(task_sequence, time_diff)

                print(
                    f"[ActionExecutor] 최종 분해 결과: {len(task_sequence)}개 세부 작업, 총 {sum(t['duration'] for t in task_sequence)}분")
                return task_sequence

            # 파싱 실패시 단순 분해
            print("[ActionExecutor] LLM 파싱 실패, 단순 분해 사용")
            return self._simple_task_decomposition(activity, duration)

        except Exception as e:
            print(f"[ActionExecutor] 작업 분해 중 오류 발생: {e}")
            return self._simple_task_decomposition(activity, duration)

    def _adjust_task_timing(self, task_sequence, time_diff):
        """세부 작업들의 시간을 조정하여 총 시간을 맞춤"""
        if time_diff > 0:  # 시간이 부족하면 추가
            # 가장 긴 작업에 시간 추가
            max_task = max(task_sequence, key=lambda x: x['duration'])
            max_task['duration'] += time_diff
        else:  # 시간이 초과하면 감소
            time_to_reduce = abs(time_diff)
            # 긴 작업들부터 시간 감소
            sorted_tasks = sorted(task_sequence, key=lambda x: x['duration'], reverse=True)
            for task in sorted_tasks:
                if time_to_reduce <= 0:
                    break
                if task['duration'] > 5:  # 최소 5분은 유지
                    reduction = min(time_to_reduce, task['duration'] - 5)
                    task['duration'] -= reduction
                    time_to_reduce -= reduction

    def _simple_task_decomposition(self, activity, duration):
        """LLM 실패시 사용할 간단한 분해 로직"""
        # 기본 장소 결정
        default_location = self.available_locations[0] if self.available_locations else "대학교:중앙광장"

        # 활동별 간단한 분해 패턴
        if "아침" in activity or "기상" in activity:
            return [
                {'task': '일어나기', 'duration': min(10, duration // 3), 'location': default_location},
                {'task': '세면하기', 'duration': min(15, duration // 3), 'location': default_location},
                {'task': '준비 마무리', 'duration': duration - min(25, 2 * duration // 3), 'location': default_location}
            ]
        elif "공부" in activity or "과제" in activity:
            return [
                {'task': '자료 준비', 'duration': min(15, duration // 4), 'location': default_location},
                {'task': '집중 학습', 'duration': duration - min(15, duration // 4), 'location': default_location}
            ]
        elif "식사" in activity:
            return [
                {'task': '메뉴 선택', 'duration': min(5, duration // 6), 'location': default_location},
                {'task': '식사하기', 'duration': duration - min(5, duration // 6), 'location': default_location}
            ]
        elif "휴식" in activity:
            return [
                {'task': '자리 찾기', 'duration': min(5, duration // 8), 'location': default_location},
                {'task': '휴식하기', 'duration': duration - min(5, duration // 8), 'location': default_location}
            ]
        else:
            # 기본: 준비 + 실행으로 분해
            prep_time = min(10, duration // 4)
            return [
                {'task': f'{activity} 준비', 'duration': prep_time, 'location': default_location},
                {'task': f'{activity} 실행', 'duration': duration - prep_time, 'location': default_location}
            ]

    def determine_next_action(self, current_time, planner):
        """다음 행동 결정 (논문 스타일 다단계 분해 적용)"""
        print(f"[ActionExecutor] {self.npc.name}의 다음 행동 결정 중... (현재 시간: {current_time.strftime('%H:%M')})")

        # 1. 현재 세부 작업이 끝났는지 확인
        if self._is_current_step_finished(current_time):
            # 2. 다음 세부 작업이 있는지 확인
            if self._has_next_step():
                self._move_to_next_step(current_time)
                return True
            else:
                # 3. 모든 세부 작업이 끝났으면 새로운 활동 시작
                return self._start_new_activity(current_time, planner)

        return False  # 현재 작업 계속

    def _is_current_step_finished(self, current_time):
        """현재 세부 작업이 끝났는지 확인"""
        if not self.current_action_sequence or not self.action_start_time:
            return True

        if self.current_step_index >= len(self.current_action_sequence):
            return True

        # 현재 세부 작업까지의 누적 시간 계산
        elapsed_minutes = (current_time - self.action_start_time).total_seconds() / 60
        cumulative_time = sum(step['duration'] for step in self.current_action_sequence[:self.current_step_index + 1])

        finished = elapsed_minutes >= cumulative_time

        if finished:
            current_step = self.current_action_sequence[self.current_step_index]
            print(f"[ActionExecutor] 세부 작업 완료: {current_step['task']} ({current_step['duration']}분)")

        return finished

    def _has_next_step(self):
        """다음 세부 작업이 있는지 확인"""
        return self.current_step_index + 1 < len(self.current_action_sequence)

    def _move_to_next_step(self, current_time):
        """다음 세부 작업으로 이동"""
        self.current_step_index += 1
        current_step = self.current_action_sequence[self.current_step_index]

        print(f"[ActionExecutor] 다음 세부 작업 시작: {current_step['task']} @ {current_step['location']}")

        # 위치 업데이트
        self.target_location = current_step['location']

        # 메모리에 기록
        self.npc.memory_manager.add_memory(
            'event',
            f"{current_step['task']}을(를) {current_step['location']}에서 시작했다",
            importance=4
        )

    def _start_new_activity(self, current_time, planner):
        """새로운 활동 시작 (논문 스타일 분해 적용)"""
        # 1. 플래너에서 현재 활동 가져오기
        activity, duration = planner.get_current_activity(current_time)
        print(f"[ActionExecutor] 새 활동 시작: '{activity}' ({duration}분)")

        # 2. 활동을 세부 작업으로 분해
        self.current_action_sequence = self._decompose_task_with_llm(activity, duration)
        self.current_step_index = 0
        self.action_start_time = current_time
        self.total_duration = duration
        self.main_activity = activity

        # 3. 첫 번째 세부 작업 시작
        if self.current_action_sequence:
            first_step = self.current_action_sequence[0]
            self.target_location = first_step['location']

            print(f"[ActionExecutor] 첫 번째 세부 작업: {first_step['task']} @ {first_step['location']}")

            # 메모리에 기록
            self.npc.memory_manager.add_memory(
                'event',
                f"'{activity}' 활동을 시작하여 첫 번째로 '{first_step['task']}'을(를) {first_step['location']}에서 시작했다",
                importance=6
            )

            return True

        return False

    def get_current_status(self):
        """현재 행동 상태 반환 (논문 스타일 적용)"""
        if not self.current_action_sequence or self.current_step_index >= len(self.current_action_sequence):
            return {
                # 기존 키 호환성 유지
                "action": "대기 중",
                "description": "다음 활동을 계획 중",
                "emoji": "🤔",
                "location": "알 수 없음",
                "progress": 0.0,

                # 논문 스타일 추가 정보
                "main_activity": "대기 중",
                "current_step": "할 일을 찾고 있음",
                "step_progress": f"0/0",
                "remaining_steps": [],
                "remaining_minutes": 0
            }

        current_step = self.current_action_sequence[self.current_step_index]

        # 전체 진행률 계산
        if self.action_start_time and self.total_duration > 0:
            from time_manager import time_manager
            current_time = time_manager.get_current_time()
            elapsed_minutes = (current_time - self.action_start_time).total_seconds() / 60
            progress = min(1.0, elapsed_minutes / self.total_duration)
            remaining_minutes = max(0, self.total_duration - elapsed_minutes)
        else:
            progress = 0.0
            remaining_minutes = 0

        # 남은 단계들
        remaining_steps = [step['task'] for step in self.current_action_sequence[self.current_step_index + 1:]]

        return {
            # 기존 키 호환성 유지 (server_autonomous.py에서 사용)
            "action": current_step['task'],
            "description": f"{current_step['location']}에서 {current_step['task']}",
            "emoji": self._get_step_emoji(current_step['task']),
            "location": current_step['location'],
            "progress": progress,

            # 논문 스타일 추가 정보
            "main_activity": self.main_activity,
            "current_step": current_step['task'],
            "step_progress": f"{self.current_step_index + 1}/{len(self.current_action_sequence)}",
            "remaining_steps": remaining_steps,
            "remaining_minutes": remaining_minutes
        }

    def _get_step_emoji(self, step_task):
        """세부 작업에 맞는 이모지 선택"""
        task_lower = step_task.lower()

        if "화장실" in task_lower or "세면" in task_lower:
            return "🚿"
        elif "옷" in task_lower or "갈아입" in task_lower:
            return "👔"
        elif "식사" in task_lower or "먹" in task_lower:
            return "🍽️"
        elif "공부" in task_lower or "문제" in task_lower or "암기" in task_lower:
            return "📚"
        elif "휴식" in task_lower or "쉬" in task_lower:
            return "😌"
        elif "자료" in task_lower or "준비" in task_lower:
            return "📋"
        elif "이동" in task_lower or "가기" in task_lower:
            return "🚶"
        else:
            return "⚡"

    def get_detailed_schedule_info(self):
        """세부 일정 정보 반환"""
        if not self.current_action_sequence:
            return "현재 진행 중인 활동이 없습니다."

        info = f"📋 {self.main_activity} (총 {self.total_duration}분)\n"
        info += "━━━━━━━━━━━━━━━━━━━━\n"

        for i, step in enumerate(self.current_action_sequence):
            status = "✅" if i < self.current_step_index else ("⏳" if i == self.current_step_index else "⏸️")
            info += f"{status} {step['task']} ({step['duration']}분) @ {step['location']}\n"

        return info

    def handle_player_interaction(self, player_location, interaction_type="chat"):
        """플레이어 상호작용 처리 (논문 스타일 적용)"""
        print(f"[ActionExecutor] 플레이어 상호작용 처리: {interaction_type}")

        # 현재 진행 중인 세부 작업 기록
        if self.current_action_sequence and self.current_step_index < len(self.current_action_sequence):
            current_step = self.current_action_sequence[self.current_step_index]
            self.npc.memory_manager.add_memory(
                'event',
                f"'{current_step['task']}' 중에 플레이어와 {interaction_type} 상호작용이 시작되었다",
                importance=7
            )

        # 상호작용으로 전환
        self.current_action_sequence = [{
            'task': "플레이어와 대화",
            'duration': 10,
            'location': player_location
        }]
        self.current_step_index = 0
        self.target_location = player_location
        self.main_activity = "플레이어와 상호작용"

        return True

    def get_unity_movement_command(self):
        """Unity에 보낼 이동 명령 생성"""
        if not self.target_location or not self.current_action_sequence:
            return None

        current_step = self.current_action_sequence[self.current_step_index] if self.current_step_index < len(
            self.current_action_sequence) else None
        if not current_step:
            return None

        return {
            "npc_id": self.npc.name,
            "target_location": self.target_location,
            "main_activity": self.main_activity,
            "current_step": current_step['task'],
            "step_progress": f"{self.current_step_index + 1}/{len(self.current_action_sequence)}",
            "emoji": self._get_step_emoji(current_step['task']),
            "movement_style": self._determine_movement_style(current_step['task'])
        }

    def _determine_movement_style(self, step_task):
        """세부 작업에 따른 이동 스타일 결정"""
        if "급" in step_task or "빨리" in step_task or "서둘" in step_task:
            return "fast"
        elif "천천히" in step_task or "여유" in step_task or "휴식" in step_task:
            return "slow"
        else:
            return "normal"