"""Nhiễm sắc thể: một phương án xếp lịch hoàn chỉnh cho mọi lớp học phần.

CÁCH MÃ HOÁ (genome)
  _slots        : mảng phẳng độ dài DAYS_NUM × DAY_HOURS × numberOfRooms
                  (5 × 13 × số phòng). Mỗi ô là danh sách lớp đang chiếm ô đó,
                  nên nhiều hơn 1 phần tử nghĩa là TRÙNG PHÒNG.
                  Chỉ số ô tính theo Reservation.getHashCode:
                      index = (ngày × sốPhòng + phòng) × 13 + tiết
                  và đi hết một ngày = 13 × sốPhòng chỉ số.
  _classes      : lớp -> chỉ số ô MỞ ĐẦU của lớp đó. Bộ ba (ngày, phòng, tiết)
                  suy ra từ chỉ số này chính là gen vị trí của lớp.
  _professors   : lớp -> giảng viên được chọn. Đây là khối gen thứ hai mà GA tiến
                  hoá (dữ liệu đầu vào không cài sẵn giảng viên cho lớp).
  _criteria     : mảng bool độ dài sốLớp × 3, sắp theo lớp (class-major):
                  cờ của lớp k, tiêu chí i nằm ở k × 3 + i với i = 0 P (phòng),
                  1 G (giảng viên), 2 N (nghỉ trưa). Xem model/Criteria.py.
  _fitness      : vô hướng [0, 1] do calculateFitness() tính, 1.0 là lịch hoàn hảo.

CÔNG THỨC FITNESS
  điểm = Σ_lớp Σ_{i∈{P,G,N}} (1 nếu đạt, nếu vi phạm trừ 1 - weights[i])
         − (số lớp bị xếp vào khung bận của giảng viên × Criteria.busyPenalty)
  fitness = điểm / len(_criteria) = điểm / (3 × số lớp)
  Vì weights = [1.0, 1.0, 1.0], một vi phạm cứng làm mất trọn 1 điểm (≈ 1/(3×sốLớp)
  fitness), còn vi phạm mềm B chỉ mất 0.2 điểm — ràng buộc mềm không bao giờ
  đắt hơn ràng buộc cứng.
"""
from .Constant import Constant
from .CourseClass import CourseClass
from .Reservation import Reservation
from .Criteria import Criteria
from numpy.random import randint as randrange

import numpy as np


# Nhiễm sắc thể lịch
class Schedule:
    # Chọn ngẫu nhiên thời gian bắt đầu sao cho lớp không rơi vào khung nghỉ trưa
    @staticmethod
    def randomTime(dur):
        """Sinh offset bắt đầu (0-based) cho một lớp dài `dur` tiết.

        Ứng viên hợp lệ là t ∈ [0, DAY_HOURS - dur] — cách lấy này bảo đảm cả dur
        tiết nằm gọn trong ngày; sau đó loại mọi t mà khối [t, t+dur) chồng lên
        offset nghỉ trưa (t <= 6 < t+6). Ràng buộc N vẫn được chấm điểm riêng,
        nên đây chỉ là bước giảm không gian mẫu khi sinh/đột biến, không phải
        chỗ duy nhất chặn nghỉ trưa.
        """
        times = [t for t in range(Constant.DAY_HOURS - dur + 1)
                 if not (t <= Constant.LUNCH_PERIOD < t + dur)]
        return times[randrange(len(times))]

    # Khởi tạo nhiễm sắc thể với khối cấu hình (thiết lập của nhiễm sắc thể)
    def __init__(self, configuration):
        self._configuration = configuration
        # Giá trị độ phù hợp của nhiễm sắc thể
        self._fitness = 0

        # Các ô thời gian - không gian, mỗi phần tử tương ứng một giờ trong một phòng học
        # daySize = DAY_HOURS × numberOfRooms là số ô của một ngày
        slots_length = Constant.DAYS_NUM * Constant.DAY_HOURS * self._configuration.numberOfRooms
        self._slots = [[] for _ in range(slots_length)]

        # Bảng lớp học phần của nhiễm sắc thể
        # Dùng để xác định ô thời gian - không gian đầu tiên mà lớp học phần sử dụng
        self._classes = {}

        # Bảng gán giảng viên của nhiễm sắc thể: lớp học phần -> giảng viên.
        # Giảng viên do GA tự gán khi tiến hoá (không còn cài sẵn trong dữ liệu).
        self._professors = {}

        # Các cờ đánh dấu sự thỏa mãn các yêu cầu của lớp học phần:
        # 3 cờ (P, G, N) cho mỗi lớp, sắp class-major nên chỉ số = k × 3 + i.
        self._criteria = np.zeros(self._configuration.numberOfCourseClasses * len(Criteria.weights), dtype=bool)

    # Chọn ngẫu nhiên một giảng viên có khả năng giảng dạy môn của lớp học phần
    def _randomProfessorFor(self, cc):
        """Rút đều 1 trong các giảng viên dạy được môn của lớp (None nếu không có).

        Danh sách tra cứu do Configuration xây từ `subjects` của từng giảng viên;
        lớp chưa có giảng viên phù hợp sẽ không gây vi phạm G và cũng không bị
        phạt B (xem Criteria.isOverlappedProf và calculateFitness).
        """
        capable = self._configuration.getProfessorsByCourse(cc.Course.Id)
        if not capable:
            return None
        return capable[randrange(len(capable))]


    def copy(self, c, setup_only):
        """Nhân bản nhiễm sắc thể.

        setup_only=True  : chỉ lấy cấu hình, trả về Schedule RỖNG (dùng cho
                           prototype và cho con lai sắp được nạp gen mới).
        setup_only=False : sao chép cả gen (slots, classes, professors), cờ
                           tiêu chí và fitness — bản sao mang nội dung giống hệt
                           cha mẹ, dùng khi lai ghép bị bỏ qua.
        """
        if not setup_only:
            self._configuration = c.configuration
            # sao chép mã
            self._slots, self._classes = [row[:] for row in c.slots], {key: value for key, value in c.classes.items()}
            # sao chép bảng gán giảng viên
            self._professors = {key: value for key, value in c.professors.items()}

            # sao chép các cờ yêu cầu của lớp học phần và giá trị độ phù hợp
            self._criteria = c.criteria[:]
            self._fitness = c.fitness
            return self

        return Schedule(c.configuration)

    # Tạo nhiễm sắc thể mới có cùng thiết lập nhưng với mã được chọn ngẫu nhiên
    def makeNewFromPrototype(self, positions = None):
        """Sinh một cá thể ngẫu nhiên: mỗi lớp được rút (ngày, phòng, tiết) đều.

        Không gian tìm kiếm của MỘT lớp:
          ngày  : DAYS_NUM = 5 lựa chọn
          phòng : numberOfRooms lựa chọn
          tiết  : các offset hợp lệ do randomTime(dur) sinh ra (không chồng nghỉ trưa)
        Tổng số phương án thô = (5 × số phòng × số tiết hợp lệ)^số lớp, vì vậy GA
        mới cần fitness dẫn đường thay vì liệt kê.

        positions: nếu truyền vào một list, ghi lần lượt [day, room, time] của mọi
        lớp để caller lần sau tái dựng đúng lịch này (dùng khi tái tạo bước trung
        gian trong báo cáo).
        """
        # tạo nhiễm sắc thể mới, sao chép thiết lập của nhiễm sắc thể
        new_chromosome = self.copy(self, True)
        new_chromosome_slots, new_chromosome_classes = new_chromosome._slots, new_chromosome._classes
        new_chromosome_professors = new_chromosome._professors

        # đặt các lớp học phần vào vị trí ngẫu nhiên
        classes = self._configuration.courseClasses
        nr = self._configuration.numberOfRooms
        DAYS_NUM, DAY_HOURS = Constant.DAYS_NUM, Constant.DAY_HOURS
        for c in classes:
            # xác định vị trí ngẫu nhiên của lớp học phần
            dur = c.Duration

            day = randrange(DAYS_NUM)
            room = randrange(nr)
            time = Schedule.randomTime(dur)
            reservation = Reservation.getReservation(nr, day, time, room)

            if positions is not None:
                positions.append(day)
                positions.append(room)
                positions.append(time)
            # hash(reservation) = chỉ số ô mở đầu (xem Reservation.getHashCode)
            reservation_index = hash(reservation)

            # điền vào các ô thời gian - không gian, với từng giờ của lớp học phần.
            # randomTime đã chặn khối [time, time+dur) vượt ngày nên index + i luôn
            # thuộc cùng một (ngày, phòng).
            for i in range(dur - 1, -1, -1):
                new_chromosome_slots[reservation_index + i].append(c)

            # chèn vào bảng lớp học phần của nhiễm sắc thể
            new_chromosome_classes[c] = reservation_index

            # gán ngẫu nhiên một giảng viên có khả năng giảng dạy môn này
            new_chromosome_professors[c] = new_chromosome._randomProfessorFor(c)

        new_chromosome.calculateFitness()
        return new_chromosome
        
    # Thực hiện phép lai ghép giữa hai nhiễm sắc thể và trả về con cái
    def crossover(self, parent, numberOfCrossoverPoints, crossoverProbability):
        """Lai ghép nhiều điểm theo TRẬT TỰ LỚP, trả về một con duy nhất (self là cha).

        Xác suất: điều kiện là randrange(100) > p thì KHÔNG lai, mà randrange(100)
        cho 0..99, nên con được lai thật sự với xác suất (p + 1) / 100.

        Cách cắt: gen được xét theo thứ tự các lớp (course_classes[i], i = 0..size-1)
        chứ không theo ô thời gian. numberOfCrossoverPoints vị trí trong dãy đó
        được chọn làm điểm cắt; giữa hai điểm cắt, con lấy nguyên (ngày, phòng,
        tiết) và giảng viên từ một cha/mẹ, rồi ĐỔI NGUỒN tại mỗi điểm cắt.
        Vì mỗi lớp lấy nguyên khối của một cha/mẹ, con luôn có đúng một vị trí cho
        mỗi lớp — không cần repair nào sau lai ghép.

        Lưu ý: _classes.keys() là thứ tự chèn, và mọi cá thể đều được sinh theo
        cùng thứ tự lớp của configuration nên các "gen i" so sánh được với nhau.
        """
        # kiểm tra xác suất thực hiện phép lai ghép
        if randrange(100) > crossoverProbability:
            # không lai ghép, chỉ sao chép cha mẹ thứ nhất
            return self.copy(self, False)

        # đối tượng nhiễm sắc thể mới, sao chép thiết lập của nhiễm sắc thể
        n = self.copy(self, True)
        n_classes, n_slots = n._classes, n._slots
        n_professors = n._professors

        classes = self._classes
        course_classes = tuple(classes.keys())
        parent_classes = parent.classes
        parent_course_classes = tuple(parent.classes.keys())
        parent_professors = parent.professors

        # số lớp học phần
        size = len(classes)

        # cp[i] = True nếu sau gen thứ i là một điểm cắt. Vị trí rút không hoàn
        # lại trong toàn bộ dãy gen nên cần k <= size; AlgorithmParameters.normalize
        # giới hạn số điểm cắt theo số lớp, nếu để lớn hơn thì vòng lặp bên dưới
        # không còn chỗ trống để rút và lặp vô hạn.
        cp = size * [False]

        # xác định điểm lai ghép (ngẫu nhiên)
        for i in range(numberOfCrossoverPoints, 0, -1):
            check_point = False
            while not check_point:
                p = randrange(size)
                if not cp[p]:
                    cp[p] = check_point = True

        # tạo mã mới bằng cách kết hợp mã của hai cha mẹ
        # first = True: đoạn hiện tại lấy từ self (cha), False: lấy từ parent (mẹ)
        first = randrange(2) == 0
        
        for i in range(size):
            if first:
                course_class = course_classes[i]
                dur = course_class.Duration
                # reservation_index = chỉ số ô mở đầu của lớp trong cha
                reservation_index = classes[course_class]
                # chèn lớp học phần từ cha mẹ thứ nhất vào bảng lớp học phần của nhiễm sắc thể mới
                n_classes[course_class] = reservation_index
                # thừa hưởng gán giảng viên từ cha mẹ thứ nhất
                n_professors[course_class] = self._professors.get(course_class)
                # sao chép toàn bộ các ô thời gian - không gian của lớp học phần
                # (dur ô liên tiếp kể từ ô mở đầu)
                for j in range(dur - 1, -1, -1):
                    n_slots[reservation_index + j].append(course_class)
            else:
                course_class = parent_course_classes[i]
                dur = course_class.Duration
                reservation_index = parent_classes[course_class]
                # chèn lớp học phần từ cha mẹ thứ hai vào bảng lớp học phần của nhiễm sắc thể mới
                n_classes[course_class] = reservation_index
                # thừa hưởng gán giảng viên từ cha mẹ thứ hai
                n_professors[course_class] = parent_professors.get(course_class)
                # sao chép toàn bộ các ô thời gian - không gian của lớp học phần
                for j in range(dur - 1, -1, -1):
                    n_slots[reservation_index + j].append(course_class)

            # điểm lai ghép: đổi nguồn cha/mẹ cho các gen kế tiếp
            if cp[i]:
                first = not first

        # Con lai được chấm điểm lại vì tổ hợp gen mới có thể tạo trùng phòng/trùng
        # giảng viên mà không cha mẹ nào có.
        n.calculateFitness()

        # trả về con trỏ thông minh tới con cái
        return n
        
    def repair(self, cc1: CourseClass, reservation1_index: int, reservation2: Reservation):
        """Dời một lớp khỏi ô cũ sang một ô khác rồi cập nhật _classes.

        reservation1_index = -1 nghĩa là lớp chưa có chỗ ở cũ (không cần gỡ).
        reservation2 = None nghĩa là chọn ô mới ngẫu nhiên theo đúng phân phối lúc
        sinh khởi tạo: ngày đều trong 5 ngày, phòng đều trong số phòng, tiết do
        randomTime(dur) chọn nên khối tiết không chồng nghỉ trưa và không tràn ngày.
        Đây là bước "sửa" duy nhất: sau khi dời, mọi ô trung gian giữa vị trí cũ và
        mới đã bị gỡ nên không còn gen nào trỏ vào ô cũ.
        """
        nr = self._configuration.numberOfRooms
        DAY_HOURS, DAYS_NUM = Constant.DAY_HOURS, Constant.DAYS_NUM
        slots = self._slots
        dur = cc1.Duration

        if reservation1_index > -1:
            for j in range(dur):
                # gỡ bỏ giờ học của lớp khỏi ô thời gian - không gian hiện tại.
                # while + remove xử lý trường hợp ô chứa lớp này nhiều lần (gen trùng
                # lặp có thể xuất hiện khi lai ghép sao chép cùng ô).
                cl = slots[reservation1_index + j]
                while cc1 in cl:
                    cl.remove(cc1)

        # xác định vị trí của lớp học phần một cách ngẫu nhiên
        if reservation2 is None:
            day = randrange(DAYS_NUM)
            room = randrange(nr)
            time = Schedule.randomTime(dur)
            reservation2 = Reservation.getReservation(nr, day, time, room)

        reservation2_index = hash(reservation2)
        for j in range(dur):
            # chuyển giờ học của lớp sang ô thời gian - không gian mới
            slots[reservation2_index + j].append(cc1)

        # thay đổi mục trong bảng lớp học phần để trỏ tới các ô thời gian - không gian mới
        self._classes[cc1] = reservation2_index

    # Thực hiện phép đột biến trên nhiễm sắc thể
    def mutation(self, mutationSize, mutationProbability):
        """Đột biến: dời tối đa mutationSize lớp sang ô ngẫu nhiên và gán lại giảng viên.

        Xác suất: randrange(100) > p thì bỏ qua, nên đột biến xảy ra với xác suất
        (p + 1) / 100. Khi xảy ra, luôn đúng mutationSize lần dời, mỗi lần rút đều
        một lớp trong sốLớp lớp — hai lần rút có thể trúng cùng một lớp, khi đó lớp
        bị dời hai lần.

        Đột biến đổi cả hai khối gen (vị trí và giảng viên) để thoát cực trị địa
        phương mà lai ghép một mình không vượt được; fitness chỉ tính một lần ở cuối.
        """
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
            # chọn ngẫu nhiên một lớp học phần để di chuyển (có thể trùng lớp đã
            # dời ở vòng trước)
            mpos = randrange(numberOfClasses)

            # ô thời gian - không gian hiện tại mà lớp học phần đang sử dụng
            cc1 = course_classes[mpos]
            reservation1_index = classes[cc1]

            # dời lớp sang ô ngẫu nhiên mới (reservation2 = None)
            self.repair(cc1, reservation1_index, None)

            # đột biến gán giảng viên: gán lại ngẫu nhiên một giảng viên phù hợp
            # (chọn trong set dạy được môn, không phải mọi giảng viên)
            self._professors[cc1] = self._randomProfessorFor(cc1)

        # một lần đột biến có thể sửa nhiều lớp nên chỉ chấm điểm sau khi xong hết
        self.calculateFitness()


    # Tính giá trị độ phù hợp của nhiễm sắc thể
    def calculateFitness(self):
        """Chấm điểm toàn bộ lịch theo công thức trong docstring đầu tệp.

        điểm_cứng = Σ_{lớp k} Σ_{i ∈ {P,G,N}} (1 nếu cờ i của lớp k đạt,
                                                  1 - weights[i] nếu vi phạm)
        điểm_mềm  = Σ_{lớp k} (busyPenalty nếu lớp k dính khung bận của GV được gán)
        fitness   = (điểm_cứng - điểm_mềm) / len(_criteria)
                  = (điểm_cứng - điểm_mềm) / (3 × số lớp)  ∈ [0, 1] (có thể âm
                    nếu trùng nghỉ trưa/room quá nhiều kết hợp phạt mềm)

        Mỗi lớp tối đa 3 điểm cứng, tương ứng 3 tiêu chí P - G - N.
        Phạt mềm B tính THEO LỚP (một lần cho dù lớp dính bao nhiêu ô bận), nên
        một lớp dài 5 tiết nằm trọn trong khung bận cũng chỉ mất 0.2 điểm.
        """
        # điểm số của nhiễm sắc thể
        score = 0

        criteria, configuration = self._criteria, self._configuration
        items, slots = self._classes.items(), self._slots
        professors = self._professors
        numberOfRooms = configuration.numberOfRooms
        DAY_HOURS, DAYS_NUM = Constant.DAY_HOURS, Constant.DAYS_NUM
        # daySize = số ô trong một ngày = 13 tiết × số phòng; tiến một bước DAY_HOURS
        # là nhảy sang cùng (ngày, tiết) của phòng kế tiếp.
        daySize = DAY_HOURS * numberOfRooms

        # ci là con trỏ vào mảng cờ: mỗi lớp chiếm 3 vị trí liên tiếp (P, G, N)
        ci = 0

        # kiểm tra các tiêu chí và tính điểm cho từng lớp học phần trong thời khóa biểu
        for cc, reservation_index in items:
            # giải mã chỉ số ô -> (ngày, tiết, phòng) qua bảng nhớ tạm Reservation
            reservation = Reservation.parse(reservation_index)

            # toạ độ của ô thời gian - không gian
            day, time = reservation.Day, reservation.Time

            dur = cc.Duration

            # P: ô mở đầu + (dur - 1) ô kế tiếp phải không có lớp khác chen vào
            ro = Criteria.isRoomOverlapped(slots, reservation, dur)

            # có bị trùng phòng không
            criteria[ci + 0] = not ro

            # G: timeId là ô (ngày, tiết) tại phòng đầu tiên; Criteria quét cửa sổ
            # [timeId, timeId + dur) trên MỌI phòng (bước nhảy DAY_HOURS = sang phòng
            # kế) để tìm lớp khác do cùng giảng viên dạy.
            timeId = day * daySize + time
            po = Criteria.isOverlappedProf(slots, cc, numberOfRooms, timeId, professors)

            # các giảng viên không có lớp học phần nào trùng lịch?
            criteria[ci + 1] = not po

            # N: lớp có phủ offset nghỉ trưa (6) không
            lunch = Criteria.isInLunchBreak(time, dur)

            # lớp học phần có xếp ngoài khung nghỉ trưa không?
            criteria[ci + 2] = not lunch

            # Cộng điểm tiêu chí: đạt 1 điểm, vi phạm trừ theo trọng số.
            # weights = [1.0, 1.0, 1.0] nên một vi phạm cứng làm mất trọn 1 điểm.
            for i in range(len(Criteria.weights)):
                if criteria[ci + i]:
                    score += 1
                else:
                    # Trọng số là mức phạt: 0 = không phạt, 1 = mất trọn điểm.
                    score += 1 - Criteria.weights[i]

            ci += len(Criteria.weights)

        # ==================== RÀNG BUỘC MỀM (SOFT CONSTRAINTS) ====================
        # Các ràng buộc mềm không bắt buộc phải đạt; mỗi vi phạm trừ một phần
        # điểm số để thuật toán GA dần tối ưu.

        # --- 1) Tránh khung giờ bận cố định của giảng viên (B) ---
        # Mỗi lớp bị xếp vào ô bận của giảng viên sẽ bị phạt busyPenalty, tính MỘT
        # lần cho lớp (break sau ô bận đầu tiên) dù lớp dài mấy tiết.
        softPenalty = 0.0
        for cc, reservation_index in items:
            prof = professors.get(cc)
            if prof is None or not prof.BusySlots:
                continue
            reservation = Reservation.parse(reservation_index)
            day, time, dur = reservation.Day, reservation.Time, cc.Duration
            for off in range(dur):
                # so theo offset 0-based, cùng hệ quy chiếu với BusySlots
                if prof.isBusyAt(day, time + off):
                    softPenalty += Criteria.busyPenalty
                    break  # chỉ phạt một lần cho mỗi lớp bị trùng khung bận

        score -= softPenalty

        # tính giá trị độ phù hợp dựa trên điểm số:
        # mẫu số len(criteria) = 3 × số lớp là tổng điểm cứng tối đa, nên
        # fitness = 1.0 khi và chỉ khi không vi phạm cứng và không dính bận.
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
    # Trả về bảng gán giảng viên của nhiễm sắc thể (lớp học phần -> giảng viên)
    def professors(self):
        return self._professors

    @property
    # Trả về mảng các cờ đánh dấu sự thỏa mãn yêu cầu của lớp học phần
    def criteria(self):
        return self._criteria

    @property
    # Trả về tham chiếu tới mảng các ô thời gian - không gian
    def slots(self):
        return self._slots
