import json

from .Professor import Professor
from .Course import Course
from .Room import Room
from .CourseClass import CourseClass


# Đọc tệp cấu hình và lưu các đối tượng đã phân tích
class Configuration:

    # Khởi tạo dữ liệu
    def __init__(self):
        # Cho biết cấu hình chưa được phân tích
        self._isEmpty = True
        # các giảng viên đã phân tích
        self._professors = {}
        # các môn học đã phân tích
        self._courses = {}
        # các phòng học đã phân tích
        self._rooms = {}
        # các lớp học phần đã phân tích
        self._courseClasses = []
        # tra cứu: ID môn -> danh sách giảng viên có khả năng giảng dạy môn đó
        self._professorsByCourse = {}

    # Trả về giảng viên có ID được chỉ định
    # Nếu không có giảng viên nào với ID đó thì hàm trả về NULL
    def getProfessorById(self, id) -> Professor:
        if id in self._professors:
            return self._professors[id]
        return None

    @property
    # Trả về số giảng viên đã phân tích
    def numberOfProfessors(self) -> int:
        return len(self._professors)

    # Trả về môn học có ID được chỉ định
    # Nếu không có môn học nào với ID đó thì hàm trả về NULL
    def getCourseById(self, id) -> Course:
        if id in self._courses:
            return self._courses[id]
        return None

    @property
    def numberOfCourses(self) -> int:
        return len(self._courses)

    # Trả về phòng học có ID được chỉ định
    # Nếu không có phòng học nào với ID đó thì hàm trả về NULL
    def getRoomById(self, id) -> Room:
        if id in self._rooms:
            return self._rooms[id]
        return None

    @property
    # Trả về số phòng học đã phân tích
    def numberOfRooms(self) -> int:
        return len(self._rooms)

    @property
    # Trả về tham chiếu tới danh sách các lớp học phần đã phân tích
    def courseClasses(self) -> []:
        return self._courseClasses

    @property
    # Trả về số lớp học phần đã phân tích
    def numberOfCourseClasses(self) -> int:
        return len(self._courseClasses)

    @property
    # Trả về TRUE nếu cấu hình chưa được phân tích
    def isEmpty(self) -> bool:
        return self._isEmpty

    # Đọc dữ liệu giảng viên từ tệp cấu hình, tạo đối tượng và trả về
    # Trả về NULL nếu hàm không thể phân tích được dữ liệu cấu config
    # Hỗ trợ: subjects (danh sách ID môn có khả năng giảng dạy),
    #         busy (danh sách khung bận {day, start, end} với start/end là
    #         chỉ số khung giờ 0-based, bao gồm cả hai đầu).
    # Mỗi giảng viên tự chọn bao nhiêu khung bận tùy ý; khung được bung thành
    # từng ô (day, time) và đó là dạng duy nhất bộ nhớ giữ lại.
    @staticmethod
    def __parseProfessor(dictConfig):
        id = 0
        name = ''
        subjects = []
        busy = []

        for key in dictConfig:
            if key == 'id':
                id = dictConfig[key]
            elif key == 'name':
                name = dictConfig[key]
            elif key == 'subjects':
                subjects = dictConfig[key] or []
            elif key == 'busy':
                for block in (dictConfig[key] or []):
                    day = block.get('day')
                    start = block.get('start', 0)
                    end = block.get('end', start)
                    if day is None:
                        continue
                    for t in range(int(start), int(end) + 1):
                        busy.append((int(day), t))

        if id == 0 or name == '':
            return None
        return Professor(id, name, subjects, busy)

    # Đọc dữ liệu môn học từ tệp cấu hình, tạo đối tượng và trả về con trỏ
    # Trả về None nếu hàm không thể phân tích được dữ liệu dictConfig
    @staticmethod
    def __parseCourse(dictConfig):
        id = 0
        name = ''

        for key in dictConfig:
            if key == 'id':
                id = dictConfig[key]
            elif key == 'name':
                name = dictConfig[key]

        if id == 0:
            return None
        return Course(id, name)

    # Đọc dữ liệu phòng học từ tệp cấu config, tạo đối tượng và trả về con trỏ
    # Trả về None nếu hàm không thể phân tích được dữ liệu cấu config
    @staticmethod
    def __parseRoom(dictConfig):
        name = ''

        for key in dictConfig:
            if key == 'name':
                name = dictConfig[key]

        if name == '':
            return None
        return Room(name)

    # Đọc dữ liệu lớp học phần từ tệp cấu hình, tạo đối tượng và trả về con trỏ
    # Trả về None nếu hàm không thể phân tích được dữ liệu cấu config
    # Lớp học phần chỉ chứa môn học + số tiết; giảng viên do GA gán khi xếp lịch.
    def __parseCourseClass(self, dictConfig):
        cid = 0
        dur = 3

        for key in dictConfig:
            if key == 'course':
                cid = dictConfig[key]
            elif key == 'duration':
                dur = dictConfig[key]

        # lấy môn học mà lớp học phần này thuộc về
        c = self.getCourseById(cid)

        # môn học có tồn tại không
        if not c:
            return None

        # tạo đối tượng và trả về (không còn giảng viên cài sẵn)
        return CourseClass(c, dur)

    # phân tích tệp và lưu các đối tượng đã phân tích
    def parseFile(self, fileName):
        # xoá các đối tượng đã phân tích trước đó
        self._professors = {}
        self._courses = {}
        self._rooms = {}
        self._courseClasses = []

        Room.restartIDs()
        CourseClass.restartIDs()

        with open(fileName, "r", encoding="utf-8") as f:
            # đọc tệp thành một chuỗi và giải mã JSON ra kiểu dữ liệu
            data = json.load(f)

        for dictConfig in data:
            for key in dictConfig:
                if key == 'prof':
                    prof = self.__parseProfessor(dictConfig[key])
                    self._professors[prof.Id] = prof
                elif key == 'course':
                    course = self.__parseCourse(dictConfig[key])
                    self._courses[course.Id] = course
                elif key == 'room':
                    room = self.__parseRoom(dictConfig[key])
                    self._rooms[room.Id] = room
                elif key == 'class':
                    courseClass = self.__parseCourseClass(dictConfig[key])
                    self._courseClasses.append(courseClass)

        # xây dựng tra cứu môn -> giảng viên có khả năng giảng dạy
        self._professorsByCourse = {}
        for professor in self._professors.values():
            for courseId in professor.Subjects:
                self._professorsByCourse.setdefault(courseId, []).append(professor)

        self._isEmpty = False

    # Trả về danh sách giảng viên có khả năng giảng dạy môn học với ID cho trước
    def getProfessorsByCourse(self, courseId):
        return self._professorsByCourse.get(courseId, [])
