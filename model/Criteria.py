from .Constant import Constant


# Đọc tệp cấu hình và lưu các đối tượng đã phân tích
class Criteria:
    # Mức phạt của MỘT vi phạm ràng buộc cứng = trọn 1 điểm của tiêu chí đó
    # (một lớp tối đa 3 điểm, ứng với P - G - N).
    hardPenalty = 1.0

    # Trọng số phạt cho từng tiêu chí cứng, theo thứ tự P (phòng),
    # G (giảng viên), N (nghỉ trưa).
    # 0 = không phạt, 1 = phạt tối đa (mất trọn 1 điểm của tiêu chí).
    # Điểm của một tiêu chí: đạt = 1; vi phạm = 1 - weight.
    weights = [hardPenalty, hardPenalty, hardPenalty]

    # kiểm tra các lớp học phần có bị trùng phòng hay không
    @staticmethod
    def isRoomOverlapped(slots, reservation, dur):
        reservation_index = hash(reservation)
        cls = slots[reservation_index: reservation_index + dur]
        return any(True for slot in cls if len(slot) > 1)

    # kiểm tra sự trùng lặp giữa các lớp học phần về giảng viên
    # professors: bảng gán giảng viên của nhiễm sắc thể (lớp -> giảng viên)
    @staticmethod
    def isOverlappedProf(slots, cc, numberOfRooms, timeId, professors):
        po = False

        prof = professors.get(cc)
        if prof is None:
            # lớp chưa được gán giảng viên -> không phát sinh trùng lịch giảng viên
            return False

        dur = cc.Duration
        for i in range(numberOfRooms, 0, -1):
            # với từng giờ của lớp học phần
            for j in range(timeId, timeId + dur):
                cl = slots[j]
                for cc1 in cl:
                    if cc != cc1:
                        # giảng viên có bị trùng lịch không?
                        if not po and professors.get(cc1) == prof:
                            po = True
                        # đã phát hiện trùng lịch giảng viên thì dừng kiểm tra
                        if po:
                            return po

            timeId += Constant.DAY_HOURS
        return po

    # kiểm tra lớp học phần có rơi vào khung giờ nghỉ trưa (12h-13h) không
    @staticmethod
    def isInLunchBreak(timeId, dur):
        # lớp học vi phạm nếu bất kỳ tiết nào của nó nằm trong khung nghỉ trưa
        return timeId <= Constant.LUNCH_PERIOD < timeId + dur

    # ------------------------------------------------------------------
    # RÀNG BUỘC MỀM (soft constraints)
    # Quy tắc: mọi trọng số mềm phải NHỎ HƠN hardPenalty (1.0), để một vi
    # phạm mềm không bao giờ đắt bằng một vi phạm cứng. GA vì thế luôn ưu
    # tiên sửa P/G/N trước, rồi mới tối ưu sự thoải mái của giảng viên.
    # B tính theo từng vi phạm.
    # ------------------------------------------------------------------

    # Trọng số phạt cho mỗi lớp bị xếp vào khung giờ bận của giảng viên (B).
    busyPenalty = 0.2
