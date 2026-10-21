from .Constant import Constant
from .CourseClass import CourseClass
from .Reservation import Reservation
from .Criteria import Criteria
from numpy.random import randint as randrange

import numpy as np

# Nhiễm sắc thể lịch
class Schedule:
    # Khởi tạo nhiễm sắc thể với khối cấu hình (thiết lập của nhiễm sắc thể)
    def __init__(self, configuration):
        self._configuration = configuration
        # Giá trị độ phù hợp của nhiễm sắc thể
        self._fitness = 0

        # Các ô thời gian - không gian, mỗi phần tử tương ứng một giờ trong một phòng học
        slots_length = Constant.DAYS_NUM * Constant.DAY_HOURS * self._configuration.numberOfRooms
        self._slots = [[] for _ in range(slots_length)]

        # Bảng lớp học phần của nhiễm sắc thể
        # Dùng để xác định ô thời gian - không gian đầu tiên mà lớp học phần sử dụng
        self._classes = {}

        # Các cờ đánh dấu sự thỏa mãn các yêu cầu của lớp học phần
        self._criteria = np.zeros(self._configuration.numberOfCourseClasses * len(Criteria.weights), dtype=bool)

    def copy(self, c, setup_only):
        if not setup_only:
            self._configuration = c.configuration
            # sao chép mã
            self._slots, self._classes = [row[:] for row in c.slots], {key: value for key, value in c.classes.items()}

            # sao chép các cờ yêu cầu của lớp học phần và giá trị độ phù hợp
            self._criteria = c.criteria[:]
            self._fitness = c.fitness
            return self

        return Schedule(c.configuration)

    # Tạo nhiễm sắc thể mới có cùng thiết lập nhưng với mã được chọn ngẫu nhiên
    def makeNewFromPrototype(self, positions = None):
        # tạo nhiễm sắc thể mới, sao chép thiết lập của nhiễm sắc thể
        new_chromosome = self.copy(self, True)
        new_chromosome_slots, new_chromosome_classes = new_chromosome._slots, new_chromosome._classes

        # đặt các lớp học phần vào vị trí ngẫu nhiên
        classes = self._configuration.courseClasses
        nr = self._configuration.numberOfRooms
        DAYS_NUM, DAY_HOURS = Constant.DAYS_NUM, Constant.DAY_HOURS
        for c in classes:
            # xác định vị trí ngẫu nhiên của lớp học phần
            dur = c.Duration

            day = randrange(DAYS_NUM)
            room = randrange(nr)
            time = randrange(DAY_HOURS - dur)
            reservation = Reservation.getReservation(nr, day, time, room)

            if positions is not None:
                positions.append(day)
                positions.append(room)
                positions.append(time)
            reservation_index = hash(reservation)

            # điền vào các ô thời gian - không gian, với từng giờ của lớp học phần
            for i in range(dur - 1, -1, -1):
                new_chromosome_slots[reservation_index + i].append(c)

            # chèn vào bảng lớp học phần của nhiễm sắc thể
            new_chromosome_classes[c] = reservation_index

        new_chromosome.calculateFitness()
        return new_chromosome
        
    # Thực hiện phép lai ghép giữa hai nhiễm sắc thể và trả về con cái
    def crossover(self, parent, numberOfCrossoverPoints, crossoverProbability):
        # kiểm tra xác suất thực hiện phép lai ghép
        if randrange(100) > crossoverProbability:
            # không lai ghép, chỉ sao chép cha mẹ thứ nhất
            return self.copy(self, False)

        # đối tượng nhiễm sắc thể mới, sao chép thiết lập của nhiễm sắc thể
        n = self.copy(self, True)
        n_classes, n_slots = n._classes, n._slots

        classes = self._classes
        course_classes = tuple(classes.keys())
        parent_classes = parent.classes
        parent_course_classes = tuple(parent.classes.keys())

        # số lớp học phần
        size = len(classes)

        cp = size * [False]

        # xác định điểm lai ghép (ngẫu nhiên)
        for i in range(numberOfCrossoverPoints, 0, -1):
            check_point = False
            while not check_point:
                p = randrange(size)
                if not cp[p]:
                    cp[p] = check_point = True

        # tạo mã mới bằng cách kết hợp mã của hai cha mẹ
        first = randrange(2) == 0
        
        for i in range(size):
            if first:
                course_class = course_classes[i]
                dur = course_class.Duration
                reservation_index = classes[course_class]
                # chèn lớp học phần từ cha mẹ thứ nhất vào bảng lớp học phần của nhiễm sắc thể mới
                n_classes[course_class] = reservation_index
                # sao chép toàn bộ các ô thời gian - không gian của lớp học phần
                for j in range(dur - 1, -1, -1):
                    n_slots[reservation_index + j].append(course_class)
            else:
                course_class = parent_course_classes[i]
                dur = course_class.Duration
                reservation_index = parent_classes[course_class]
                # chèn lớp học phần từ cha mẹ thứ hai vào bảng lớp học phần của nhiễm sắc thể mới
                n_classes[course_class] = reservation_index
                # sao chép toàn bộ các ô thời gian - không gian của lớp học phần
                for j in range(dur - 1, -1, -1):
                    n_slots[reservation_index + j].append(course_class)

            # điểm lai ghép
            if cp[i]:
                # đổi nhiễm sắc thể nguồn
                first = not first

        n.calculateFitness()

        # trả về con trỏ thông minh tới con cái
        return n
        
    def repair(self, cc1: CourseClass, reservation1_index: int, reservation2: Reservation):
        nr = self._configuration.numberOfRooms
        DAY_HOURS, DAYS_NUM = Constant.DAY_HOURS, Constant.DAYS_NUM
        slots = self._slots
        dur = cc1.Duration

        if reservation1_index > -1:
            for j in range(dur):
                # gỡ bỏ giờ học của lớp khỏi ô thời gian - không gian hiện tại
                cl = slots[reservation1_index + j]
                while cc1 in cl:
                    cl.remove(cc1)

        # xác định vị trí của lớp học phần một cách ngẫu nhiên
        if reservation2 is None:
            day = randrange(DAYS_NUM)
            room = randrange(nr)
            time = randrange(DAY_HOURS - dur)
            reservation2 = Reservation.getReservation(nr, day, time, room)

        reservation2_index = hash(reservation2)
        for j in range(dur):
            # chuyển giờ học của lớp sang ô thời gian - không gian mới
            slots[reservation2_index + j].append(cc1)

        # thay đổi mục trong bảng lớp học phần để trỏ tới các ô thời gian - không gian mới
        self._classes[cc1] = reservation2_index

    # Thực hiện phép đột biến trên nhiễm sắc thể
    def mutation(self, mutationSize, mutationProbability):
        # kiểm tra xác suất thực hiện phép đột biến
        if randrange(100) > mutationProbability:
            return

        classes = self._classes
        # số lớp học phần
        numberOfClasses = len(classes)
        course_classes = tuple(classes.keys())
        configuration = self._configuration
        nr = configuration.numberOfRooms

        # di chuyển số lớp học phần được chọn đến vị trí ngẫu nhiên
        for i in range(mutationSize, 0, -1):
            # chọn ngẫu nhiên một lớp học phần để di chuyển
            mpos = randrange(numberOfClasses)

            # ô thời gian - không gian hiện tại mà lớp học phần đang sử dụng
            cc1 = course_classes[mpos]
            reservation1_index = classes[cc1]

            self.repair(cc1, reservation1_index, None)

        self.calculateFitness()

    # Tính giá trị độ phù hợp của nhiễm sắc thể
    def calculateFitness(self):
        # điểm số của nhiễm sắc thể
        score = 0

        criteria, configuration = self._criteria, self._configuration
        items, slots = self._classes.items(), self._slots
        numberOfRooms = configuration.numberOfRooms
        DAY_HOURS, DAYS_NUM = Constant.DAY_HOURS, Constant.DAYS_NUM
        daySize = DAY_HOURS * numberOfRooms

        ci = 0
        getRoomById = configuration.getRoomById

        # kiểm tra các tiêu chí và tính điểm cho từng lớp học phần trong thời khóa biểu
        for cc, reservation_index in items:
            reservation = Reservation.parse(reservation_index)

            # toạ độ của ô thời gian - không gian
            day, time, room = reservation.Day, reservation.Time, reservation.Room

            dur = cc.Duration

            ro = Criteria.isRoomOverlapped(slots, reservation, dur)

            # có bị trùng phòng không
            criteria[ci + 0] = not ro

            r = getRoomById(room)
            # phòng hiện tại có đủ chỗ ngồi không
            criteria[ci + 1] = Criteria.isSeatEnough(r, cc)

            # kiểm tra sự trùng lặp giữa các lớp học phần về giảng viên và nhóm sinh viên
            timeId = day * daySize + time
            po, go = Criteria.isOverlappedProfStudentGrp(slots, cc, numberOfRooms, timeId)

            # các giảng viên không có lớp học phần nào trùng lịch?
            criteria[ci + 2] = not po

            # các nhóm sinh viên không có lớp học phần nào trùng lịch?
            criteria[ci + 3] = not go

            for i in range(len(Criteria.weights)):
                if criteria[ci + i]:
                    score += 1
                else:
                    # Trọng số là mức phạt: 0 = không phạt, 1 = mất trọn điểm.
                    score += 1 - Criteria.weights[i]

            ci += len(Criteria.weights)

        # tính giá trị độ phù hợp dựa trên điểm số
        self._fitness = score / len(criteria)

    # Trả về giá trị độ phù hợp của nhiễm sắc thể
    @property
    def fitness(self):
        return self._fitness

    @property
    def configuration(self):
        return self._configuration

    @property
    # Trả về tham chiếu tới bảng lớp học phần
    def classes(self):
        return self._classes

    @property
    # Trả về mảng các cờ đánh dấu sự thỏa mãn yêu cầu của lớp học phần
    def criteria(self):
        return self._criteria

    @property
    # Trả về tham chiếu tới mảng các ô thời gian - không gian
    def slots(self):
        return self._slots
