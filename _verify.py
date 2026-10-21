"""Chạy GASchedule (GA), in thời khóa biểu và kiểm tra tính hợp lệ."""
import pathlib
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path().absolute()))

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

from model.Configuration import Configuration
from model.Reservation import Reservation
from model.Constant import Constant
from algorithm.GeneticAlgorithm import GeneticAlgorithm

DAYS = ("T2", "T3", "T4", "T5", "T6")
PERIODS = [""] + [
    f"Tiết {period} ({Constant.START_HOUR + period - 1}-"
    f"{Constant.START_HOUR + period})"
    for period in range(1, Constant.DAY_HOURS + 1)
]

config = Configuration()
config.parseFile(str(pathlib.Path().absolute()) + "/GaSchedule.json")

print(f"Số phòng: {config.numberOfRooms} | Số giảng viên: {config.numberOfProfessors} | "
      f"Số nhóm SV: {config.numberOfStudentGroups} | Số buổi học: {config.numberOfCourseClasses}")
print("Đang chạy thuật toán GA ...\n")
alg = GeneticAlgorithm(config)
alg.run()
best = alg.result
print(f"\nĐộ phù hợp cuối cùng: {best.fitness:.6f}\n")

crit = best.criteria
n = len(crit) // 4
NAMES = ["P - Phòng học trùng lịch", "C - Đủ số chỗ ngồi",
         "G - Giảng viên trùng lịch", "S - Nhóm SV trùng lịch"]
print("--- Điểm từng tiêu chí ---")
for i, nm in enumerate(NAMES):
    fails = [j for j in range(n) if not crit[j * 4 + i]]
    print(f"  {nm:<24}: {'OK' if not fails else f'{len(fails)}/{n} VI PHAM'}")

# --- Kiểm tra trùng lịch trực tiếp từ Schedule ---
room_occ, prof_occ, grp_occ = defaultdict(set), defaultdict(set), defaultdict(set)
conf_room = conf_prof = conf_grp = seat_bad = 0

for cc, idx in best.classes.items():
    res = Reservation.parse(idx)
    room = config.getRoomById(res.Room)
    if room.NumberOfSeats < cc.NumberOfSeats:
        seat_bad += 1
    for j in range(cc.Duration):
        slot = (res.Day, res.Time + j)
        if slot in room_occ[res.Room]:
            conf_room += 1
        room_occ[res.Room].add(slot)
        if slot in prof_occ[cc.Professor.Id]:
            conf_prof += 1
        prof_occ[cc.Professor.Id].add(slot)
        for g in cc.Groups:
            if slot in grp_occ[g.Id]:
                conf_grp += 1
            grp_occ[g.Id].add(slot)

print("\n--- Kiểm tra độc lập ---")
print(f"  Trùng lịch phòng học     : {conf_room}")
print(f"  Trùng lịch giảng viên    : {conf_prof}")
print(f"  Trùng lịch nhóm sinh viên: {conf_grp}")
print(f"  Phòng không đủ chỗ ngồi : {seat_bad}")
total_bad = conf_room + conf_prof + conf_grp + seat_bad
print(f"\n=> {'THỜI KHÓA BIỂU HOÀN TOÀN HỢP LỆ' if total_bad == 0 else f'CÒN {total_bad} LỖI'}")

# --- In thời khóa biểu ---
grid = defaultdict(dict)
for cc, idx in best.classes.items():
    res = Reservation.parse(idx)
    label = f"{cc.Course.Name} / {cc.Professor.Name} / {'+'.join(g.Name for g in cc.Groups)}"
    grid[res.Room][(res.Day, res.Time)] = (cc.Duration, label)

for room_id in range(config.numberOfRooms):
    room = config.getRoomById(room_id)
    print("\n" + "=" * 150)
    print(f"PHÒNG {room.Name}   Số chỗ: {room.NumberOfSeats}")
    print("=" * 150)
    print(f"{'Tiết':<20}" + "".join(f"| {d:<26}" for d in DAYS))
    print("-" * 150)
    for p in range(Constant.DAY_HOURS):
        row = f"{PERIODS[p + 1]:<20}"
        for d in range(Constant.DAYS_NUM):
            dur, label = grid[room_id].get((d, p), (0, ""))
            if label:
                tag = f" [{dur}h]" if dur > 1 else ""
                row += f"| {(label[:22] + tag):<26}"
            elif p > 0 and grid[room_id].get((d, p - 1), (0, ""))[0] > 1:
                row += f"| {'^ (tiếp)':<26}"
            else:
                row += f"| {'':<26}"
        print(row)

# --- Thống kê ---
tot = sum(c.Duration for c in config.courseClasses)
sua_chua = Constant.DAY_HOURS * Constant.DAYS_NUM * config.numberOfRooms
print("\n" + "=" * 150)
print("THỐNG KÊ")
print("=" * 150)
print(f"  Tổng số giờ học trong tuần : {tot}")
print(f"  Sức chứa phòng học         : {Constant.DAY_HOURS} tiết x {Constant.DAYS_NUM} ngày"
      f" x {config.numberOfRooms} phòng = {sua_chua} giờ")
print(f"  Tỉ lệ sử dụng             : {tot / sua_chua * 100:.1f}%")