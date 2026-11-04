"""Bộ kiểm tra ràng buộc dùng khi chấm điểm một nhiễm sắc thể.

Ba HÀM kiểm tra ở đây trả về True = CÓ VI PHẠM; Schedule.calculateFitness đảo cờ
và cộng điểm theo công thức:

    đóng_góp_của_tiêu_chí_i = 1 nếu đạt, 1 - weights[i] nếu vi phạm

weights đồng nhất bằng hardPenalty = 1.0 nên mỗi vi phạm cứng (P, G hoặc N) làm
mất trọn 1 điểm của lớp đó; mỗi lớp có tối đa 3 điểm. Ràng buộc mềm B chỉ trừ
busyPenalty = 0.2 cho mỗi lớp dính khung bận và được áp ở Schedule, không ở đây.

Thứ tự tiêu chí cứng khớp với chỉ số cờ trong _criteria: 0 = P (Phòng),
1 = G (Giảng viên), 2 = N (Nghỉ trưa); cùng thứ tự với Criteria.weights và với
HtmlOutput.CRITERIAS.
"""
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
    # Độ dài mảng này cũng chính là số tiêu chí cứng trên mỗi lớp, được dùng làm
    # bước nhảy khi đọc _criteria (k × 3 + i).
    weights = [hardPenalty, hardPenalty, hardPenalty]

    # kiểm tra các lớp học phần có bị trùng phòng hay không
    @staticmethod
    def isRoomOverlapped(slots, reservation, dur):
        """P: True nếu một trong dur ô của lớp còn chứa lớp khác.

        slots là mảng phẳng index = (ngày × số phòng + phòng) × DAY_HOURS + tiết,
        nên dur tiết liền nhau của cùng một lớp là dur ô liên tiếp, bắt đầu từ
        hash(reservation). Slice [idx, idx + dur) vì thế nằm trọn trong khối của
        một (ngày, phòng) — randomTime bảo đảm khối không tràn sang ngày/phòng khác.
        len(ô) > 1 nghĩa là có ít nhất hai lớp chiếm cùng một tiết trong cùng phòng.
        """
        reservation_index = hash(reservation)
        cls = slots[reservation_index: reservation_index + dur]
        return any(True for slot in cls if len(slot) > 1)

    # kiểm tra sự trùng lặp giữa các lớp học phần về giảng viên
    # professors: bảng gán giảng viên của nhiễm sắc thể (lớp -> giảng viên)
    @staticmethod
    def isOverlappedProf(slots, cc, numberOfRooms, timeId, professors):
        """G: True nếu cùng giảng viên còn dạy lớp khác trong khung tiết của lớp này.

        timeId = ngày × (DAY_HOURS × số phòng) + tiết, tức ô (ngày, tiết) của
        PHÒNG ĐẦU TIÊN. Vì hai ô cùng tiết ở hai phòng kế nhau chênh đúng
        DAY_HOURS chỉ số, mỗi vòng lặp `timeId += DAY_HOURS` là nhảy sang phòng kế
        trong cùng ngày; chạy numberOfRooms vòng là quét hết mọi phòng.

        Trong mỗi phòng, cửa sổ [timeId, timeId + dur) là đúng dur tiết mà lớp cc
        chiếm, nên phát hiện được trùng lịch kể cả khi hai lớp ở hai phòng khác
        nhau. Điều kiện cc != cc1 loại chính lớp đang xét; hàm return ngay khi thấy
        vi phạm đầu tiên.
        """
        po = False

        prof = professors.get(cc)
        if prof is None:
            # lớp chưa được gán giảng viên -> không phát sinh trùng lịch giảng viên
            return False

        dur = cc.Duration
        # biến lặp chỉ để đếm đủ số phòng; vị trí thật do timeId dịch chuyển
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

            # sang phòng kế trong cùng (ngày, tiết): cộng đúng độ dài một ngày
            timeId += Constant.DAY_HOURS
        return po

    # kiểm tra lớp học phần có rơi vào khung giờ nghỉ trưa (12h-13h) không
    @staticmethod
    def isInLunchBreak(timeId, dur):
        """N: True nếu khối tiết [timeId, timeId + dur) phủ lên offset nghỉ trưa.

        Điều kiện timeId <= LUNCH_PERIOD < timeId + dur là phép thử giao nhau của
        hai khoảng nửa mở, với LUNCH_PERIOD = 6. Vì randomTime khi sinh khởi tạo
        và khi đột biến đã tránh khung này, cờ N thường chỉ bật lên do lai ghép
        ghép các đoạn của hai cha mẹ lại với nhau.
        """
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
    # 0.2 điểm / lớp, quy đổi ra fitness là 0.2 / (3 × số lớp).
    busyPenalty = 0.2

