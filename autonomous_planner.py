# autonomous_planner.py - 논문 스타일 Task Decomposition 연동 버전
import random
import re


class AutonomousPlanner:
    """NPC의 자율적 일일 계획 수립을 담당하는 클래스 (논문 스타일 적용)"""

    def __init__(self, npc_agent, llm_utils):
        self.npc = npc_agent
        self.llm_utils = llm_utils

        # 계획 상태 (논문 스타일)
        self.daily_requirements = []  # 하루 전체 요구사항 (논문의 daily_req)
        self.daily_schedule = []  # 시간별 활동 스케줄 (논문의 f_daily_schedule)
        self.daily_schedule_original = []  # 원본 시간별 스케줄 (논문의 f_daily_schedule_hourly_org)
        self.current_activity_index = 0
        self.last_planning_date = None
        self.wake_up_hour = 7

        # Unity로부터 받을 이동 가능 장소 목록
        self.available_locations = []

    def set_available_locations(self, locations: list):
        """Unity 환경에서 사용 가능한 장소 목록을 설정"""
        self.available_locations = locations
        print(f"[{self.npc.name}의 Planner] 사용 가능한 장소 목록 업데이트: {self.available_locations}")

    def should_replan(self, current_time):
        """새로운 계획이 필요한지 확인 (논문 스타일)"""
        current_date = current_time.date()

        # 새로운 날이거나 계획이 없으면 재계획
        if (not self.last_planning_date or
                self.last_planning_date != current_date or
                not self.daily_schedule):
            return True

        return False

    def generate_wake_up_hour(self):
        """기상 시간 생성 (논문의 generate_wake_up_hour 참조)"""
        prompt = f"""
        다음은 NPC의 정보입니다:
        {self.npc.persona}

        이 NPC의 성격과 생활 패턴을 고려할 때, 보통 몇 시에 일어날까요?
        6시에서 10시 사이의 숫자 하나로만 답해주세요.

        예시: 8
        """

        try:
            response = self.llm_utils.get_llm_response(prompt, temperature=0.1, max_tokens=10)
            wake_up = max(6, min(10, int(response.strip())))
            self.wake_up_hour = wake_up
            print(f"[AutonomousPlanner] 기상 시간 결정: {wake_up}시")
            return wake_up
        except:
            self.wake_up_hour = 7
            return 7

    def generate_daily_requirements(self, wake_up_hour):
        """일일 요구사항 생성 (논문의 generate_first_daily_plan 참조)"""

        # 최근 기억과 대화 컨텍스트 수집
        recent_memories = self.npc.memory_manager.retrieve_recent_memories(count=5)
        memory_summary = "\n".join([f"- {m.description}" for m in recent_memories])
        conversation_summary = self.npc.conversation_manager.get_conversation_summary()
        locations_str = ", ".join(self.available_locations) if self.available_locations else "지정된 장소가 없음"

        prompt = f"""
        당신은 {self.npc.name}의 하루 계획을 세우는 AI입니다.

        ### NPC 기본 정보 ###
        {self.npc.persona}

        ### 최근 기억 및 경험 ###
        {memory_summary}

        ### 최근 대화 요약 ###
        {conversation_summary}

        ### 사용 가능한 장소 ###
        {locations_str}

        ### 지시사항 ###
        위 정보를 바탕으로 {self.npc.name}의 하루 목표와 해야 할 일들을 4-6개의 주요 활동으로 나열해주세요.
        각 활동은 NPC의 성격, 전공, 최근 경험을 반영해야 합니다.
        특히, 활동들은 '사용 가능한 장소' 목록 내에서 수행할 수 있는 것들이어야 합니다.

        형식: 각 줄마다 한 가지 활동만 작성
        예시:
        도서관에서 졸업 작품 아이디어 구상하기
        과방에서 수학 과제 완료하기
        친구와 카페에서 대화하기
        기숙사에서 충분한 휴식 취하기

        응답:
        """

        try:
            response = self.llm_utils.get_llm_response(prompt, temperature=0.4, max_tokens=200)

            # 응답에서 활동 목록 추출
            activities = []
            for line in response.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('###'):
                    # 앞의 숫자나 특수문자 제거
                    clean_line = re.sub(r'^[\d\.\-\*\•]\s*', '', line)
                    if clean_line:
                        activities.append(clean_line)

            self.daily_requirements = activities if activities else [
                "하루를 계획적으로 보내기",
                "학업에 집중하기",
                "적절한 휴식 취하기",
                "사회적 관계 유지하기"
            ]

            print(f"[AutonomousPlanner] 일일 요구사항 생성: {len(self.daily_requirements)}개")
            for i, req in enumerate(self.daily_requirements, 1):
                print(f"  {i}. {req}")

            return self.daily_requirements

        except Exception as e:
            print(f"[AutonomousPlanner] 일일 요구사항 생성 오류: {e}")
            self.daily_requirements = [
                "하루를 계획적으로 보내기",
                "학업에 집중하기",
                "적절한 휴식 취하기"
            ]
            return self.daily_requirements

    def generate_hourly_schedule(self, daily_requirements, wake_up_hour):
        """시간별 스케줄 생성 (논문의 generate_hourly_schedule 참조)"""

        requirements_str = "\n".join([f"- {req}" for req in daily_requirements])
        locations_str = ", ".join(self.available_locations) if self.available_locations else "지정된 장소가 없음"

        prompt = f"""
        다음은 {self.npc.name}의 하루 목표입니다:
        {requirements_str}

        ### NPC 정보 ###
        {self.npc.persona}

        ### 사용 가능한 장소 ###
        {locations_str}

        ### 지시사항 ###
        {wake_up_hour}시에 일어나서 하루 종일(24시간) 동안의 활동을 시간 순서대로 계획해주세요.
        각 활동은 위의 하루 목표를 달성하는 데 도움이 되어야 하며, 지정된 장소에서만 이루어져야 합니다.

        ### 중요한 규칙 ###
        1. 모든 활동 시간의 합이 정확히 1440분(24시간)이 되어야 함
        2. 각 활동은 30분 이상이어야 함 (잠자기 제외)
        3. 반드시 위에 제시된 장소에서만 활동 가능
        4. 시간 순서를 논리적으로 배치할 것

        ### 응답 형식 ###
        각 줄을 다음과 같이 작성해주세요:
        활동명, 지속시간(분)

        예시:
        기상 및 아침 루틴, 60
        아침 식사, 45
        졸업 작품 구상, 120
        점심 식사, 60
        수학 공부, 180
        휴식 및 간식, 90
        저녁 식사, 60
        개인 시간, 150
        잠자기, 675

        응답:
        """

        try:
            response = self.llm_utils.get_llm_response(prompt, temperature=0.3, max_tokens=400)
            print(f"[AutonomousPlanner] 시간별 스케줄 LLM 응답: {response}")

            schedule = []
            total_minutes = 0

            # 응답 파싱
            lines = response.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line or ',' not in line:
                    continue

                try:
                    parts = [part.strip() for part in line.split(',')]
                    if len(parts) >= 2:
                        activity = parts[0]
                        # 숫자만 추출
                        duration_match = re.findall(r'\d+', parts[1])
                        if duration_match:
                            duration = int(duration_match[0])

                            # 최소 시간 검증 (잠자기 제외)
                            if duration >= 30 or "잠" in activity:
                                schedule.append([activity, duration])
                                total_minutes += duration
                                print(f"[AutonomousPlanner] 활동 추가: {activity} ({duration}분)")

                except (ValueError, IndexError) as e:
                    print(f"[AutonomousPlanner] 파싱 오류: {line} - {e}")
                    continue

            # 시간 조정 로직 (논문 스타일)
            schedule = self._adjust_schedule_timing(schedule, total_minutes, 1440)

            # 원본 스케줄 저장 (논문의 f_daily_schedule_hourly_org)
            self.daily_schedule_original = schedule.copy()

            print(f"[AutonomousPlanner] 최종 스케줄: {len(schedule)}개 활동, 총 {sum(s[1] for s in schedule)}분")
            return schedule

        except Exception as e:
            print(f"[AutonomousPlanner] 스케줄 생성 오류: {e}")
            return self._get_default_schedule()

    def _adjust_schedule_timing(self, schedule, current_total, target_total):
        """스케줄 시간 조정 (논문의 시간 압축 로직 참조)"""
        if not schedule:
            return self._get_default_schedule()

        time_diff = target_total - current_total

        if abs(time_diff) <= 10:  # 10분 이내 차이면 그대로
            return schedule

        if time_diff > 0:  # 시간 부족 - 활동 연장
            # 잠자기가 있으면 잠자기에 추가, 없으면 새로 추가
            sleep_found = False
            for activity in schedule:
                if "잠" in activity[0]:
                    activity[1] += time_diff
                    sleep_found = True
                    break

            if not sleep_found:
                schedule.append(["잠자기", time_diff])

        else:  # 시간 초과 - 활동 단축
            excess = abs(time_diff)
            # 긴 활동부터 단축 (잠자기 우선)
            sorted_schedule = sorted(schedule, key=lambda x: x[1], reverse=True)

            for activity in sorted_schedule:
                if excess <= 0:
                    break

                if activity[1] > 60:  # 60분 이상인 활동만 단축
                    reduction = min(excess, activity[1] - 30)  # 최소 30분은 유지
                    activity[1] -= reduction
                    excess -= reduction

        return schedule

    def _get_default_schedule(self):
        """기본 스케줄 반환"""
        return [
            ["기상 및 아침 루틴", 60],
            ["아침 식사", 60],
            ["오전 공부", 180],
            ["점심 식사", 60],
            ["오후 활동", 180],
            ["휴식", 120],
            ["저녁 식사", 60],
            ["개인 시간", 120],
            ["잠자기", 600]
        ]

    def create_new_daily_plan(self, current_time):
        """새로운 하루 계획 생성 (논문 스타일 전체 프로세스)"""
        print(f"[AutonomousPlanner] {self.npc.name}의 새로운 하루 계획 생성 중...")

        if not self.available_locations:
            print(f"[AutonomousPlanner] 경고: 사용 가능한 장소 목록이 비어있습니다.")
            return

        # 1. 기상 시간 결정 (논문의 generate_wake_up_hour)
        wake_up_hour = self.generate_wake_up_hour()

        # 2. 일일 요구사항 생성 (논문의 generate_first_daily_plan)
        daily_requirements = self.generate_daily_requirements(wake_up_hour)

        # 3. 시간별 스케줄 생성 (논문의 generate_hourly_schedule)
        self.daily_schedule = self.generate_hourly_schedule(daily_requirements, wake_up_hour)

        # 4. 현재 활동 인덱스 설정
        self.current_activity_index = self._find_current_activity_index(current_time)

        # 5. 계획을 메모리에 저장
        self._save_plan_to_memory(current_time, daily_requirements)

        # 6. 계획 날짜 업데이트
        self.last_planning_date = current_time.date()

        print(f"[AutonomousPlanner] 계획 생성 완료!")
        self._print_schedule_summary()

    def _find_current_activity_index(self, current_time):
        """현재 시간에 해당하는 활동 인덱스 찾기 (논문의 get_f_daily_schedule_index 참조)"""

        # 현재 시간이 기상 시간 이전이면 잠자기 상태
        if current_time.hour < self.wake_up_hour:
            # 잠자기 활동 찾기
            for i, (activity, _) in enumerate(self.daily_schedule):
                if "잠" in activity:
                    return i
            return len(self.daily_schedule) - 1  # 마지막 활동

        # 기상 시간부터의 경과 시간 계산
        elapsed_minutes = (current_time.hour - self.wake_up_hour) * 60 + current_time.minute
        if elapsed_minutes < 0:
            elapsed_minutes = 0

        accumulated_minutes = 0

        for i, (activity, duration) in enumerate(self.daily_schedule):
            if accumulated_minutes <= elapsed_minutes < accumulated_minutes + duration:
                print(f"[AutonomousPlanner] 현재 활동: {i}번째 - {activity}")
                return i
            accumulated_minutes += duration

        return len(self.daily_schedule) - 1  # 마지막 활동

    def _save_plan_to_memory(self, current_time, daily_requirements):
        """계획을 장기 기억에 저장 (논문 스타일)"""

        # 일일 요구사항을 기억으로 저장
        requirements_summary = ", ".join(daily_requirements[:3])
        plan_memory = f"{current_time.strftime('%Y년 %m월 %d일')} 계획: {requirements_summary}"

        self.npc.memory_manager.add_memory(
            'thought',
            plan_memory,
            importance=8
        )

        # 주요 활동들도 개별적으로 저장
        for requirement in daily_requirements[:3]:  # 상위 3개만
            self.npc.memory_manager.add_memory(
                'thought',
                f"오늘 {requirement}을(를) 해야 한다",
                importance=6
            )

    def get_current_activity(self, current_time):
        """현재 시간에 해당하는 활동 반환 (논문 스타일)"""
        if not self.daily_schedule:
            return "대기 중", 30

        # 현재 활동 인덱스 업데이트
        new_index = self._find_current_activity_index(current_time)

        if new_index != self.current_activity_index:
            print(f"[AutonomousPlanner] 활동 변경: {self.current_activity_index} -> {new_index}")
            self.current_activity_index = new_index

        if self.current_activity_index < len(self.daily_schedule):
            activity, duration = self.daily_schedule[self.current_activity_index]
            return activity, duration

        return "대기 중", 30

    def _print_schedule_summary(self):
        """스케줄 요약 출력"""
        print("\n=== 📅 오늘의 일정 ===")
        elapsed_minutes = 0

        for i, (activity, duration) in enumerate(self.daily_schedule):
            hour = self.wake_up_hour + elapsed_minutes // 60
            minute = elapsed_minutes % 60

            status = "→ " if i == self.current_activity_index else "  "
            print(f"{status}{hour:02d}:{minute:02d} - {activity} ({duration}분)")

            elapsed_minutes += duration
        print("=" * 25)

    def get_schedule_summary(self):
        """스케줄 요약 반환"""
        if not self.daily_schedule:
            return "계획이 없습니다."

        summary = f"📋 {self.npc.name}의 오늘 일정\n"
        summary += "━━━━━━━━━━━━━━━━━━━━\n"
        elapsed_minutes = 0

        for i, (activity, duration) in enumerate(self.daily_schedule):
            hour = self.wake_up_hour + elapsed_minutes // 60
            minute = elapsed_minutes % 60

            status = "▶️ " if i == self.current_activity_index else "⏸️ "
            summary += f"{status}{hour:02d}:{minute:02d} - {activity} ({duration}분)\n"

            elapsed_minutes += duration

        return summary

    def modify_schedule_for_interaction(self, interaction_type, duration_minutes):
        """상호작용으로 인한 스케줄 수정 (논문의 _create_react 참조)"""
        print(f"[AutonomousPlanner] 스케줄 수정: {interaction_type} ({duration_minutes}분)")

        # 현재 활동이 있으면 조정
        if self.current_activity_index < len(self.daily_schedule):
            current_activity, current_duration = self.daily_schedule[self.current_activity_index]

            if current_duration > duration_minutes:
                # 현재 활동 시간 단축
                self.daily_schedule[self.current_activity_index][1] -= duration_minutes
                print(f"[AutonomousPlanner] '{current_activity}' 시간을 {duration_minutes}분 단축")
            else:
                # 현재 활동을 나중으로 연기
                self.daily_schedule.insert(
                    self.current_activity_index + 1,
                    [current_activity, current_duration]
                )

                # 현재 위치에 상호작용 삽입
                self.daily_schedule[self.current_activity_index] = [interaction_type, duration_minutes]
                print(f"[AutonomousPlanner] '{current_activity}'를 연기하고 '{interaction_type}' 삽입")

    def should_interact_with_player(self, player_location, current_time):
        """플레이어와 상호작용할지 결정 (논문의 _should_react 참조)"""
        current_activity, _ = self.get_current_activity(current_time)

        # 바쁜 활동 중에는 상호작용 가능성 낮음
        busy_activities = ["시험", "중요한", "수업", "잠자기", "급한"]
        if any(busy_word in current_activity for busy_word in busy_activities):
            return False, "바쁨"

        # 사회적 활동 중이면 상호작용 가능성 높음
        social_activities = ["휴식", "카페", "식사", "산책", "자유", "개인"]
        if any(social_word in current_activity for social_word in social_activities):
            return True, "사회적"

        # 기본적으로는 70% 확률
        return random.random() > 0.3, "보통"

    def get_remaining_schedule(self):
        """남은 일정 반환"""
        if not self.daily_schedule or self.current_activity_index >= len(self.daily_schedule):
            return []

        return self.daily_schedule[self.current_activity_index + 1:]

    def debug_schedule_status(self, current_time):
        """스케줄 상태 디버깅 (논문 스타일)"""
        print("=" * 60)
        print(f"[DEBUG] 📊 {self.npc.name}의 스케줄 상태")
        print(f"[DEBUG] 현재 시간: {current_time.strftime('%H:%M')}")
        print(f"[DEBUG] 기상 시간: {self.wake_up_hour}:00")
        print(f"[DEBUG] 현재 활동 인덱스: {self.current_activity_index}")
        print(f"[DEBUG] 일일 요구사항: {self.daily_requirements}")
        print(f"[DEBUG] 전체 스케줄:")

        elapsed_minutes = 0
        for i, (activity, duration) in enumerate(self.daily_schedule):
            start_hour = self.wake_up_hour + elapsed_minutes // 60
            start_minute = elapsed_minutes % 60
            end_minute = elapsed_minutes + duration
            end_hour = self.wake_up_hour + end_minute // 60
            end_minute = end_minute % 60

            status = "🔥 " if i == self.current_activity_index else "   "
            print(
                f"{status}{i:2d}: {start_hour:02d}:{start_minute:02d}-{end_hour:02d}:{end_minute:02d} {activity} ({duration}분)")

            elapsed_minutes += duration

        print("=" * 60)