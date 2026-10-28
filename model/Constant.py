class Constant:
    # Số ngày trong một tuần
    DAYS_NUM = 5
    # Giờ bắt đầu làm việc trong ngày
    START_HOUR = 7
    # Số khung giờ trong một ngày:
    #   buổi sáng  5 tiết  (7h - 12h)  -> chỉ số 0..4
    #   nghỉ trưa  1 khung  (12h - 13h) -> chỉ số LUNCH_PERIOD
    #   buổi chiều 5 tiết  (13h - 18h) -> chỉ số 6..10
    DAY_HOURS = 11
    # Chỉ số (bắt đầu từ 0) của khung giờ nghỉ trưa 12h-13h trong ngày.
    # Xếp lịch vào khung giờ này là vi phạm ràng buộc cứng N.
    LUNCH_PERIOD = 5
    # Số tiết dạy thực sự trong một ngày (không kể khung nghỉ trưa)
    TEACHING_HOURS = DAY_HOURS - 1
