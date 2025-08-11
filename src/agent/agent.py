# wumpus_world/agent/agent.py

# Đảm bảo bạn đã import InferenceModule thay vì InferenceEngine cũ
from .inference_module import InferenceModule
from .planning_module import PlanningModule
from utils.constants import (
    N_DEFAULT,
    K_DEFAULT,
    PERCEPT_STENCH,
    PERCEPT_BREEZE,
    PERCEPT_GLITTER,
    PERCEPT_SCREAM,
    PERCEPT_BUMP,
    ACTION_MOVE_FORWARD,
    ACTION_TURN_LEFT,
    ACTION_TURN_RIGHT,
    ACTION_GRAB,
    ACTION_SHOOT,
    ACTION_CLIMB_OUT,
    NORTH,
    EAST,
    SOUTH,
    WEST,
    DIRECTIONS,
)
import random


class WumpusWorldAgent:
    def __init__(self, N=N_DEFAULT, K=K_DEFAULT):
        self.N = N
        self.K = K
        # Sử dụng InferenceModule đã được tái cấu trúc
        self.inference_module = InferenceModule(N, K)
        self.planning_module = PlanningModule(N)

        self.agent_pos = (0, 0)
        self.agent_dir = EAST
        self.agent_has_gold = False
        self.agent_has_arrow = True
        self.score = 0

        self.path_to_follow = []
        self.last_action = None
        self.last_shoot_dir = None

    def update_state(self, env_state):
        """Cập nhật trạng thái cơ bản của agent từ môi trường."""
        self.agent_pos = env_state["agent_pos"]
        self.agent_dir = env_state["agent_dir"]
        self.agent_has_gold = env_state["agent_has_gold"]
        self.agent_has_arrow = env_state["agent_has_arrow"]
        self.score = env_state["score"]

    def update_knowledge(self, percepts):
        """
        Kích hoạt InferenceModule để cập nhật Knowledge Base dựa trên các cảm nhận mới.
        """
        # Toàn bộ logic suy luận và cập nhật KB giờ đây được xử lý gọn gàng bên trong InferenceModule.
        self.inference_module.update_knowledge(
            self.agent_pos,
            percepts,
            last_action=self.last_action,
            last_shoot_dir=self.last_shoot_dir,
        )
        # Không cần xử lý 'Scream' ở đây nữa, vì InferenceModule đã tự làm điều đó.

    def decide_action(self, percepts):
        """
        Logic ra quyết định chính của agent.
        """
        # 1. Suy nghĩ: Xử lý cảm nhận và cập nhật cơ sở tri thức (KB)
        self.update_knowledge(percepts)
        
        # Đặt lại hướng bắn sau khi KB đã được cập nhật
        self.last_shoot_dir = None 

        # 2. Hành động tức thời dựa trên ưu tiên
        if PERCEPT_GLITTER in percepts:
            self.last_action = ACTION_GRAB
            return ACTION_GRAB

        if self.agent_has_gold:
            if self.agent_pos == (0, 0):
                self.last_action = ACTION_CLIMB_OUT
                return ACTION_CLIMB_OUT
            else:
                # Nếu đã có vàng, lên kế hoạch đường về nhà bằng mọi giá
                path_to_origin = self.planning_module.find_path(
                    self.agent_pos,
                    self.agent_dir,
                    (0, 0),
                    self.inference_module.get_kb_status(),
                    self.inference_module.get_visited_cells(),
                    avoid_dangerous=False,  # Có thể phải đi qua ô không chắc chắn để về
                )
                if path_to_origin:
                    self.path_to_follow = path_to_origin
                    # Rút hành động tiếp theo từ đường đi đã lên kế hoạch
                    next_action = self.path_to_follow.pop(0)
                    self.last_action = next_action
                    return next_action

        # 3. Nếu đang đi theo một lộ trình, tiếp tục đi
        if self.path_to_follow:
            next_action = self.path_to_follow.pop(0)
            self.last_action = next_action
            return next_action

        # 4. Lên kế hoạch mới: Ưu tiên khám phá các ô an toàn chưa ghé thăm
        kb_status = self.inference_module.get_kb_status()
        visited_cells = self.inference_module.get_visited_cells()
        safe_unvisited_cells = []
        for x in range(self.N):
            for y in range(self.N):
                if kb_status[x][y] == "Safe" and not visited_cells[x][y]:
                    safe_unvisited_cells.append((x, y))

        if safe_unvisited_cells:
            safe_unvisited_cells.sort(
                key=lambda p: abs(p[0] - self.agent_pos[0]) + abs(p[1] - self.agent_pos[1])
            )
            for target_cell in safe_unvisited_cells:
                path = self.planning_module.find_path(
                    self.agent_pos,
                    self.agent_dir,
                    target_cell,
                    kb_status,
                    visited_cells,
                    avoid_dangerous=True,
                )
                if path:
                    self.path_to_follow = path
                    next_action = self.path_to_follow.pop(0)
                    self.last_action = next_action
                    return next_action

        # 5. Xem xét hành động rủi ro: Bắn Wumpus
        if self.agent_has_arrow and self.inference_module.possible_wumpus:
            # Logic này có thể được cải thiện để chọn Wumpus có khả năng cao nhất
            target_wumpus = list(self.inference_module.possible_wumpus)[0]

            # Tìm một vị trí an toàn kề bên ô nghi ngờ có Wumpus để bắn
            safe_shooting_spots = []
            neighbors_of_wumpus = self.inference_module.kb._get_neighbors(target_wumpus[0], target_wumpus[1])
            for neighbor in neighbors_of_wumpus:
                if kb_status[neighbor[0]][neighbor[1]] == "Safe":
                    safe_shooting_spots.append(neighbor)
            
            if safe_shooting_spots:
                safe_shooting_spots.sort(
                    key=lambda p: abs(p[0] - self.agent_pos[0]) + abs(p[1] - self.agent_pos[1])
                )
                shooting_spot = safe_shooting_spots[0]

                # Lên kế hoạch đi đến vị trí bắn
                path_to_shoot = self.planning_module.find_path(
                    self.agent_pos,
                    self.agent_dir,
                    shooting_spot,
                    kb_status,
                    visited_cells,
                    avoid_dangerous=True,
                )

                if path_to_shoot:
                    # Lên kế hoạch quay mặt về phía Wumpus và bắn
                    # (Đây là một phiên bản đơn giản, cần logic phức tạp hơn để tính hướng cuối cùng)
                    target_dir_vec = (target_wumpus[0] - shooting_spot[0], target_wumpus[1] - shooting_spot[1])
                    
                    # Cần một hàm để chuyển đổi từ hướng hiện tại sang hướng mục tiêu
                    # Ví dụ: plan_turns(current_dir, target_dir) -> [ACTION_TURN_LEFT, ...]
                    # Để đơn giản, ta sẽ giả định việc quay hướng được xử lý sau
                    # TODO: Cải thiện logic quay để bắn
                    
                    self.path_to_follow = path_to_shoot + [ACTION_SHOOT]
                    self.last_shoot_dir = target_dir_vec
                    next_action = self.path_to_follow.pop(0)
                    self.last_action = next_action
                    return next_action

        # 6. Nếu không còn lựa chọn an toàn nào, quay về (0,0) và thoát
        if self.agent_pos != (0, 0):
            path_to_origin = self.planning_module.find_path(
                self.agent_pos,
                self.agent_dir,
                (0, 0),
                kb_status,
                visited_cells,
                avoid_dangerous=True,
            )
            if path_to_origin:
                self.path_to_follow = path_to_origin
                next_action = self.path_to_follow.pop(0)
                self.last_action = next_action
                return next_action
        
        # 7. Hành động cuối cùng: Nếu bị kẹt hoàn toàn, thử quay tại chỗ hy vọng mở ra hướng đi mới
        # Hoặc nếu không có đường về, có thể cân nhắc leo ra ngoài
        if self.agent_pos == (0, 0):
             self.last_action = ACTION_CLIMB_OUT
             return ACTION_CLIMB_OUT

        # Nếu không thể làm gì khác, quay phải
        self.last_action = ACTION_TURN_RIGHT
        return ACTION_TURN_RIGHT

    def get_known_map(self):
        """Lấy bản đồ các đối tượng đã biết từ KB."""
        return self.inference_module.get_known_map()

    def get_kb_status(self):
        """Lấy bản đồ trạng thái suy luận từ KB cho planner."""
        return self.inference_module.get_kb_status()