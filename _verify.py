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
from model.Criteria import Criteria
from algorithm.GeneticAlgorithm import GeneticAlgorithm

DAYS = ("T2", "T3", "T4", "T5", "T6")
PERIODS = [""] + [
    "Nghỉ trưa ({})".format(Constant.lunchRange(sep="-"))
    if offset == Constant.LUNCH_PERIOD
    else "Tiết {} ({})".format(
        Constant.periodNumber(offset), Constant.periodTimeRange(offset, sep="-"))
    for offset in range(Constant.DAY_HOURS)
]

config = Configuration()
config.parseFile(str(pathlib.Path().absolute()) + "/GaSchedule.json")

print(f"Số phòng: {config.numberOfRooms} | Số giảng viên: {config.numberOfProfessors} | "
      f"Số buổi học: {config.numberOfCourseClasses}")
print("Đang chạy thuật toán GA ...\n")
alg = GeneticAlgorithm(config)
alg.run()
best = alg.result
print(f"\nĐộ phù hợp cuối cùng: {best.fitness:.6f}\n")

crit = best.criteria
n = len(crit) // 3
NAMES = ["P - Phòng học trùng lịch",
         "G - Giảng viên trùng lịch",
         "N - Xếp vào khung nghỉ trưa 12-13"]
print("--- Điểm từng tiêu chí ---")
for i, nm in enumerate(NAMES):
    fails = [j for j in range(n) if not crit[j * len(NAMES) + i]]
    print(f"  {nm:<28}: {'OK' if not fails else f'{len(fails)}/{n} VI PHAM'}")


# --- Kiểm tra trùng lịch trực tiếp từ Schedule ---
room_occ, prof_occ = defaultdict(set), defaultdict(set)
conf_room = conf_prof = conf_lunch = 0

for cc, idx in best.classes.items():
    res = Reservation.parse(idx)
    if res.Time <= Constant.LUNCH_PERIOD < res.Time + cc.Duration:
        conf_lunch += 1
    for j in range(cc.Duration):
        slot = (res.Day, res.Time + j)
        if slot in room_occ[res.Room]:
            conf_room += 1
        room_occ[res.Room].add(slot)
        prof = best.professors.get(cc)
        profId = prof.Id if prof is not None else None
        if slot in prof_occ[profId]:
            conf_prof += 1
        prof_occ[profId].add(slot)

print("\n--- Kiểm tra độc lập ---")
print(f"  CỨNG - trùng phòng học     : {conf_room}")
print(f"  CỨNG - trùng GV            : {conf_prof}")
print(f"  CỨNG - khung nghỉ trưa     : {conf_lunch}")

# Ràng buộc mềm: lớp xếp vào khung giờ bận của giảng viên (phạt nhẹ hơn ràng buộc cứng)
busy_conflicts = 0
for cc, idx in best.classes.items():
    prof = best.professors.get(cc)
    if prof is None or not prof.BusySlots:
        continue
    res = Reservation.parse(idx)
    if any(prof.isBusyAt(res.Day, res.Time + j) for j in range(cc.Duration)):
        busy_conflicts += 1

print(f"  MỀM  - lớp dính khung GV bận: {busy_conflicts} "
      f"(phạt ×{Criteria.busyPenalty:g}/lớp, cứng ×{Criteria.hardPenalty:g})")

total_bad = conf_room + conf_prof + conf_lunch
print(f"=> {'THỜI KHÓA BIỂU HỢP LỆ (ràng buộc cứng)' if total_bad == 0 else f'CÒN {total_bad} LỖI CỨNG'}")

# --- In thời khóa biểu ---
grid = defaultdict(dict)
for cc, idx in best.classes.items():
    res = Reservation.parse(idx)
    prof = best.professors.get(cc)
    prof_name = prof.Name if prof is not None else "—"
    label = f"{cc.Course.Name} / {prof_name}"
    grid[res.Room][(res.Day, res.Time)] = (cc.Duration, label)

for room_id in range(config.numberOfRooms):
    room = config.getRoomById(room_id)
    print("\n" + "=" * 150)
    print(f"PHÒNG {room.Name}")
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
sua_chua = Constant.TEACHING_HOURS * Constant.DAYS_NUM * config.numberOfRooms
print("\n" + "=" * 150)
print("THỐNG KÊ")
print("=" * 150)
print(f"  Tổng số giờ học trong tuần : {tot}")
print(f"  Sức chứa phòng học         : {Constant.TEACHING_HOURS} tiết x {Constant.DAYS_NUM} ngày"
      f" x {config.numberOfRooms} phòng = {sua_chua} giờ")
print(f"  Tỉ lệ sử dụng             : {tot / sua_chua * 100:.1f}%")
