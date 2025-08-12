# wumpus_world/agent/agent.py

# Agent chỉ cần biết về giao diện cấp cao nhất của hệ thống suy luận
from .inference_module import InferenceModule 
from .planning_module import PlanningModule
from utils.constants import (
    N_DEFAULT, K_DEFAULT, PERCEPT_STENCH, PERCEPT_GLITTER,
    ACTION_MOVE_FORWARD, ACTION_TURN_LEFT, ACTION_TURN_RIGHT,
    ACTION_GRAB, ACTION_SHOOT, ACTION_CLIMB_OUT, EAST, DIRECTIONS,
)
import random

class WumpusWorldAgent:
    """
    Đại diện cho một agent thông minh.
    Vai trò: Ra quyết định chiến lược (làm gì tiếp theo) dựa trên thông tin
    được cung cấp bởi InferenceModule và PlanningModule.
    """
    def __init__(self, N=N_DEFAULT, K=K_DEFAULT):
        self.N = N
        self.K = K
        # Agent sở hữu các module chức năng của nó
        self.inference_module = InferenceModule(N, K)
        self.planning_module = PlanningModule(N)

        # Trạng thái vật lý của Agent
        self.agent_pos = (0, 0)
        self.agent_dir = EAST
        self.agent_has_gold = False
        self.agent_has_arrow = True
        self.score = 0

        # Trạng thái kế hoạch của Agent
        self.path_to_follow = []
        self.last_action = None
        self.last_shoot_dir = None

    def _get_neighbors(self, pos):
        """Hàm tiện ích để tìm các ô kề. Đây là logic về thế giới, không phải suy luận."""
        x, y = pos
        neighbors = []
        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.N and 0 <= ny < self.N:
                neighbors.append((nx, ny))
        return neighbors

    def update_state(self, env_state):
        """Đồng bộ trạng thái vật lý của agent với môi trường."""
        self.agent_pos = env_state["agent_pos"]
        self.agent_dir = env_state["agent_dir"]
        self.agent_has_gold = env_state["agent_has_gold"]
        self.agent_has_arrow = env_state["agent_has_arrow"]
        self.score = env_state["score"]

    def update_knowledge(self, percepts):
        """
        Ra lệnh cho InferenceModule cập nhật cơ sở tri thức.
        Agent không cần biết việc cập nhật diễn ra như thế nào.
        """
        self.inference_module.update_knowledge(
            self.agent_pos,
            percepts,
            last_action=self.last_action,
            last_shoot_dir=self.last_shoot_dir,
        )

    def decide_action(self, percepts):
        """
        Logic ra quyết định chiến lược chính của agent.
        Quy trình: Suy nghĩ -> Lên kế hoạch -> Hành động.
        """
        # 1. SUY NGHĨ: Cập nhật cơ sở tri thức dựa trên những gì vừa cảm nhận.
        self.update_knowledge(percepts)
        self.last_shoot_dir = None # Đặt lại trạng thái sau khi đã dùng để suy luận

        # 2. ƯU TIÊN HÀNG ĐẦU: Các hành động phản xạ, có giá trị cao.
        if PERCEPT_GLITTER in percepts:
            self.last_action = ACTION_GRAB
            return ACTION_GRAB

        if self.agent_has_gold:
            if self.agent_pos == (0, 0):
                self.last_action = ACTION_CLIMB_OUT
                return ACTION_CLIMB_OUT
            else:
                # Mục tiêu duy nhất là về nhà, bất chấp rủi ro.
                path = self.planning_module.find_path(
                    self.agent_pos, self.agent_dir, (0, 0),
                    self.inference_module.get_kb_status(),
                    self.inference_module.get_visited_cells(),
                    avoid_dangerous=False)
                if path:
                    self.path_to_follow = path

        # 3. THỰC THI KẾ HOẠCH: Nếu đang có sẵn một lộ trình, tiếp tục đi theo.
        if self.path_to_follow:
            next_action = self.path_to_follow.pop(0)
            self.last_action = next_action
            return next_action

        # 4. LÊN KẾ HOẠCH MỚI (An toàn): Tìm và đi đến ô an toàn gần nhất chưa ghé thăm.
        kb_status = self.inference_module.get_kb_status()
        visited_cells = self.inference_module.get_visited_cells()
        safe_unvisited_cells = [
            (x, y) for x in range(self.N) for y in range(self.N)
            if kb_status[x][y] == "Safe" and not visited_cells[x][y]
        ]

        if safe_unvisited_cells:
            safe_unvisited_cells.sort(key=lambda p: abs(p[0] - self.agent_pos[0]) + abs(p[1] - self.agent_pos[1]))
            for target in safe_unvisited_cells:
                path = self.planning_module.find_path(
                    self.agent_pos, self.agent_dir, target,
                    kb_status, visited_cells, avoid_dangerous=True)
                if path:
                    self.path_to_follow = path
                    return self.path_to_follow.pop(0)

        # 5. LÊN KẾ HOẠCH MỚI (Rủi ro): Nếu không còn lựa chọn an toàn, hãy xem xét việc bắn Wumpus.
        # TODO: Một agent cao cấp hơn sẽ tính toán xác suất và lợi ích kỳ vọng của việc bắn.
        if self.agent_has_arrow:
            possible_wumpus_cells = [
                (x, y) for x in range(self.N) for y in range(self.N)
                if kb_status[x][y] == "Unknown" and "W?" in self.inference_module.kb.get_facts((x, y))
            ]
            if possible_wumpus_cells:
                target_wumpus = possible_wumpus_cells[0] # Chọn mục tiêu một cách ngây thơ
                
                # Tìm vị trí an toàn kề bên để bắn
                safe_shooting_spots = [
                    pos for pos in self._get_neighbors(target_wumpus)
                    if kb_status[pos[0]][pos[1]] == "Safe"
                ]

                if safe_shooting_spots:
                    shooting_spot = min(safe_shooting_spots, key=lambda p: abs(p[0] - self.agent_pos[0]) + abs(p[1] - self.agent_pos[1]))
                    
                    path = self.planning_module.find_path(
                        self.agent_pos, self.agent_dir, shooting_spot,
                        kb_status, visited_cells, avoid_dangerous=True)
                    
                    if path:
                        # TODO: Cần một hàm để lên kế hoạch các hành động quay người (Turn)
                        # để đối mặt với Wumpus trước khi bắn.
                        target_dir_vec = (target_wumpus[0] - shooting_spot[0], target_wumpus[1] - shooting_spot[1])
                        path.append(ACTION_SHOOT)
                        self.path_to_follow = path
                        self.last_shoot_dir = target_dir_vec
                        return self.path_to_follow.pop(0)

        # 6. PHƯƠNG ÁN DỰ PHÒNG: Cố gắng quay về nhà an toàn và thoát ra (nếu có thể)
        if self.agent_pos != (0, 0):
             path_to_origin = self.planning_module.find_path(
                self.agent_pos, self.agent_dir, (0, 0),
                kb_status, visited_cells, avoid_dangerous=True)
             if path_to_origin:
                 self.path_to_follow = path_to_origin
                 return self.path_to_follow.pop(0)

        # 7. HÀNH ĐỘNG CUỐI CÙNG: Nếu bị kẹt hoàn toàn, hãy leo ra (nếu ở ô 0,0) hoặc quay tại chỗ.
        if self.agent_pos == (0, 0):
            self.last_action = ACTION_CLIMB_OUT
            return ACTION_CLIMB_OUT
        
        self.last_action = ACTION_TURN_RIGHT
        return ACTION_TURN_RIGHT

    def get_known_map(self):
        """Lấy bản đồ các đối tượng đã biết từ KB để hiển thị."""
        return self.inference_module.get_known_map()

    def get_kb_status(self):
        """Lấy bản đồ trạng thái suy luận từ KB cho planner."""
        return self.inference_module.get_kb_status()