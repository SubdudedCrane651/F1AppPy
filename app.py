# app.py
import sys
from PyQt6 import QtWidgets, QtCore
from db import get_team_points, init_db, get_seasons, get_races_for_season, get_results_for_race, debug_list_tables,debug_race_results_columns
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QTabWidget,
    QPushButton,
    QTableView,
    QHeaderView,
    QVBoxLayout,
    QListWidget,
)

from PyQt6.QtGui import QIcon

import os
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

def add_team_logos_to_horizontal_bars(ax, teams, logo_dir="assets/team_logos", pixel_size=20):
    bars = ax.patches

    for bar, team in zip(bars, teams):
        filename = f"{team.replace(' ', '_')}_logo.png"
        path = os.path.join(logo_dir, filename)

        if not os.path.exists(path):
            print(f"Logo not found for {team}: {path}")
            continue

        img = mpimg.imread(path)

        # Create a small image box (pixel_size controls the size)
        imagebox = OffsetImage(img, zoom=pixel_size / 100.0)  
        imagebox.image.axes = ax

        # Position: left side of the bar, centered vertically
        x = bar.get_x() + 2
        y = bar.get_y() + bar.get_height() / 2

        ab = AnnotationBbox(
            imagebox,
            (x, y),
            frameon=False,
            box_alignment=(0, 0.5),
            xycoords='data',
            zorder=10
        )

        ax.add_artist(ab)
TEAM_COLORS = {
    "Red Bull": "#3671C6",
    "Ferrari": "#F91536",
    "Mercedes": "#6CD3BF",
    "McLaren": "#FF8000",
    "Aston Martin": "#229971",
    "Alpine": "#0090FF",
    "Williams": "#00A0DE",
    "RB": "#6692FF",
    "Kick Sauber": "#52E252",
    "Haas": "#B6BABD",
}

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MplCanvas(FigureCanvas):
    def __init__(self, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)

class ResultsTableModel(QtCore.QAbstractTableModel):
    def __init__(self, data, headers):
        super().__init__()
        self._data = data
        self._headers = headers

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role):
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            row = self._data[index.row()]
            key = self._headers[index.column()]
            return row.get(key)
        return None

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if orientation == QtCore.Qt.Orientation.Horizontal:
                return self._headers[section]
            return section + 1
        
class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("F1 Stats Explorer")
        self.setWindowIcon(QIcon("F1_logo.png"))

        self.season_combo = QtWidgets.QComboBox()
        self.race_combo = QtWidgets.QComboBox()
        self.table = QtWidgets.QTableView()
        self.tab_team = QtWidgets.QWidget()               # 1) Create the widget
        self._build_tab_team()                  # 2) Build its layout


        self._season_map = {}
        self._race_map = {}

        self.tabs = QtWidgets.QTabWidget()
        self.results_tab = QtWidgets.QWidget()
        self.lapchart_tab = QtWidgets.QWidget()
        self.telemetry_tab = QtWidgets.QWidget()
        self.circuit_tab = QtWidgets.QWidget()
        self.strategy_tab = QtWidgets.QWidget()
        self.pitstop_tab = QtWidgets.QWidget()
        self.sector_tab = QtWidgets.QWidget()
        self.stats_tab = QtWidgets.QWidget()

        self.tabs.addTab(self.results_tab, "Results")
        self.tabs.addTab(self.lapchart_tab, "Lap Chart")
        self.tabs.addTab(self.telemetry_tab, "Telemetry")
        self.tabs.addTab(self.circuit_tab, "Circuit Map")
        self.tabs.addTab(self.strategy_tab, "Tyre Strategy")
        self.tabs.addTab(self.pitstop_tab, "Pit Stops")
        self.tabs.addTab(self.sector_tab, "Sectors")
        self.tabs.addTab(self.stats_tab, "Driver Stats")
        self.tabs.addTab(self.tab_team, "Team Performance")

        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("Season:"))
        top.addWidget(self.season_combo)
        top.addWidget(QtWidgets.QLabel("Race:"))
        top.addWidget(self.race_combo)

        res_layout = QtWidgets.QVBoxLayout()
        res_layout.addLayout(top)
        res_layout.addWidget(self.table)
        self.results_tab.setLayout(res_layout)

        self.build_lapchart_tab()
        self.build_telemetry_tab()
        self.build_circuit_tab()
        self.build_strategy_tab()
        self.build_pitstop_tab()
        self.build_sector_tab()
        self.build_stats_tab()

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

        self.load_seasons()

        self.season_combo.currentIndexChanged.connect(self.on_season_changed)
        self.race_combo.currentIndexChanged.connect(self.on_race_changed)
        self.table.clicked.connect(self.on_driver_clicked)

    # ---------- Seasons / Races ----------
    def load_seasons(self):
        seasons = get_seasons()
        self.season_combo.clear()
        self._season_map.clear()
        for s in seasons:
            label = str(s["year"])
            self.season_combo.addItem(label)
            self._season_map[label] = s["season_id"]
        if seasons:
            self.on_season_changed(0)

    def update_team_performance(self):
            rows = get_team_points()
            teams = [r["constructor_name"] for r in rows]
            points = [r["total_points"] for r in rows]

            colors = [TEAM_COLORS.get(t, "#888888") for t in teams]

            ax = self.team_canvas.ax
            ax.clear()

            if teams:
                # Draw bars FIRST
                ax.barh(teams, points, color=colors)

                # Add logos AFTER bars exist
                add_team_logos_to_horizontal_bars(ax, teams)

                ax.set_title("Team Performance (Total Points)")
                ax.set_xlabel("Points")
                self.team_canvas.fig.tight_layout()
            else:
                ax.text(
                    0.5, 0.5, "No data",
                    ha="center", va="center",
                    transform=ax.transAxes
                )

            self.team_canvas.draw()      

    def on_season_changed(self, index):
        if index < 0:
            return

        label = self.season_combo.currentText()
        season_id = self._season_map[label]

        races = get_races_for_season(season_id)
        self.races = races  # <-- FIX #1

        self.race_combo.clear()
        self._race_map.clear()

        for r in races:
            lbl = f"R{r['round']:02d} - {r['name']}"
            self.race_combo.addItem(lbl, userData=r["race_id"])
            self._race_map[lbl] = r["race_id"]  # <-- FIX #2

        if races:
            self.on_race_changed(0)

    def on_race_changed(self, index):
        if index < 0:
            return
        label = self.race_combo.currentText()
        race_id = self.race_combo.currentData()
        results = get_results_for_race(race_id)

        data = []
        for r in results:
            data.append({
                "Pos": r["finish_position"],
                "Grid": r["grid_position"],
                "Code": r["driver_code"],
                "Driver": r["driver_name"],
                "Team": r["constructor_name"],
                "Pts": r["points"],
                "Status": r["status"],
                "Laps": r["laps_completed"],
                "Time": r["time_text"],
                "FL Rank": r["fastest_lap_rank"],
                "FL Time": r["fastest_lap_time"],
            })

        headers = ["Pos", "Grid", "Code", "Driver", "Team", "Pts",
                   "Status", "Laps", "Time", "FL Rank", "FL Time"]

        model = ResultsTableModel(data, headers)
        self.table.setModel(model)
        self.table.resizeColumnsToContents()

        self.driver1_combo.clear()
        self.driver2_combo.clear()
        for r in results:
            code = r["driver_code"]
            if code:
                self.driver1_combo.addItem(code)
                self.driver2_combo.addItem(code)

    # ---------- Driver popup ----------
    def on_driver_clicked(self, index):
        row = index.row()
        model = self.table.model()
        driver_code = model._data[row]["Code"]
        driver_name = model._data[row]["Driver"]
        team_name = model._data[row]["Team"]
        season = int(self.season_combo.currentText())
        round_num = int(self.race_combo.currentText().split(" ")[0][1:])

        import fastf1
        session = fastf1.get_session(season, round_num, 'R')
        session.load()

        from driver_info import DriverInfoWindow
        self.info_window = DriverInfoWindow(session, driver_code, driver_name, team_name, season)
        self.info_window.show()

    # ---------- Lap Chart ----------
    def build_lapchart_tab(self):
        layout = QtWidgets.QVBoxLayout()
        self.lapchart_button = QtWidgets.QPushButton("Generate Lap Chart")
        self.lapchart_button.clicked.connect(self.generate_lap_chart)
        self.lapchart_canvas = None
        layout.addWidget(self.lapchart_button)
        self.lapchart_tab.setLayout(layout)

    def generate_lap_chart(self):
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
        import matplotlib.pyplot as plt
        import fastf1

        if self.race_combo.count() == 0:
            return
        label = self.race_combo.currentText()
        season = int(self.season_combo.currentText())
        round_num = int(label.split(" ")[0][1:])
        session = fastf1.get_session(season, round_num, 'R')
        session.load()

        fig, ax = plt.subplots(figsize=(10, 6))
        for drv in session.drivers:
            laps = session.laps.pick_driver(drv)
            if laps.empty:
                continue
            code = session.get_driver(drv)["Abbreviation"]
            ax.plot(laps["LapNumber"], laps["Position"], label=code)
        ax.invert_yaxis()
        ax.set_xlabel("Lap")
        ax.set_ylabel("Position")
        ax.set_title(f"Lap Chart - {label}")
        ax.legend(ncol=3, fontsize=8)

        if self.lapchart_canvas:
            self.lapchart_canvas.setParent(None)
        self.lapchart_canvas = FigureCanvasQTAgg(fig)
        self.lapchart_tab.layout().addWidget(self.lapchart_canvas)

    def _build_tab_team(self):
        layout = QVBoxLayout(self.tab_team)

        # Matplotlib canvas for the bar chart
        self.team_canvas = MplCanvas(width=6, height=4, dpi=100)
        layout.addWidget(self.team_canvas)

        # Refresh button
        btn = QPushButton("Refresh Team Performance")
        btn.clicked.connect(self.update_team_performance)
        layout.addWidget(btn)        

    # ---------- Telemetry ----------
    def build_telemetry_tab(self):
        layout = QtWidgets.QVBoxLayout()
        self.driver1_combo = QtWidgets.QComboBox()
        self.driver2_combo = QtWidgets.QComboBox()
        self.telemetry_button = QtWidgets.QPushButton("Generate Telemetry Overlay")
        self.telemetry_button.clicked.connect(self.generate_telemetry_overlay)
        self.telemetry_canvas = None
        layout.addWidget(QtWidgets.QLabel("Driver 1"))
        layout.addWidget(self.driver1_combo)
        layout.addWidget(QtWidgets.QLabel("Driver 2"))
        layout.addWidget(self.driver2_combo)
        layout.addWidget(self.telemetry_button)
        self.telemetry_tab.setLayout(layout)

    def generate_telemetry_overlay(self):
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
        import matplotlib.pyplot as plt
        import fastf1

        d1 = self.driver1_combo.currentText()
        d2 = self.driver2_combo.currentText()
        if not d1 or not d2 or d1 == d2:
            return
        label = self.race_combo.currentText()
        season = int(self.season_combo.currentText())
        round_num = int(label.split(" ")[0][1:])
        session = fastf1.get_session(season, round_num, 'R')
        session.load()

        laps1 = session.laps.pick_driver(d1)
        laps2 = session.laps.pick_driver(d2)
        if laps1.empty or laps2.empty:
            return
        lap1 = laps1.pick_fastest()
        lap2 = laps2.pick_fastest()
        tel1 = lap1.get_car_data().add_distance()
        tel2 = lap2.get_car_data().add_distance()

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(tel1["Distance"], tel1["Speed"], label=f"{d1} Speed")
        ax.plot(tel2["Distance"], tel2["Speed"], label=f"{d2} Speed")
        ax.set_xlabel("Distance (m)")
        ax.set_ylabel("Speed (km/h)")
        ax.set_title(f"Telemetry Overlay (Fastest Lap) - {label}")
        ax.legend()

        if self.telemetry_canvas:
            self.telemetry_canvas.setParent(None)
        self.telemetry_canvas = FigureCanvasQTAgg(fig)
        self.telemetry_tab.layout().addWidget(self.telemetry_canvas)

    # ---------- Circuit Map ----------
    def build_circuit_tab(self):
        layout = QtWidgets.QVBoxLayout()
        self.circuit_button = QtWidgets.QPushButton("Show Circuit Map")
        self.circuit_button.clicked.connect(self.show_circuit_map)
        self.circuit_canvas = None
        layout.addWidget(self.circuit_button)
        self.circuit_tab.setLayout(layout)

    def show_circuit_map(self):
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
        import matplotlib.pyplot as plt
        import fastf1

        if self.race_combo.count() == 0:
            return

        label = self.race_combo.currentText()
        season = int(self.season_combo.currentText())
        round_num = int(label.split(" ")[0][1:])

        session = fastf1.get_session(season, round_num, 'R')
        session.load()

        # Get all laps
        laps = session.laps
        if laps.empty:
            return

        # Pick the fastest lap of the entire race
        fastest_lap = laps.pick_fastest()

        # Now get position data for that lap
        pos = fastest_lap.get_pos_data()
        if pos is None or pos.empty:
            return

        fig, ax = plt.subplots(figsize=(6, 6))
        ax.plot(pos["X"], pos["Y"], linewidth=2)
        ax.set_aspect("equal", "box")
        ax.set_title(f"Circuit Map - {label}")
        ax.axis("off")

        if self.circuit_canvas:
            self.circuit_canvas.setParent(None)

        self.circuit_canvas = FigureCanvasQTAgg(fig)
        self.circuit_tab.layout().addWidget(self.circuit_canvas)

    # ---------- Tyre Strategy ----------
    def build_strategy_tab(self):
        layout = QtWidgets.QVBoxLayout()
        self.strategy_button = QtWidgets.QPushButton("Show Tyre Strategy (simple)")
        self.strategy_button.clicked.connect(self.show_strategy)
        self.strategy_list = QtWidgets.QListWidget()
        layout.addWidget(self.strategy_button)
        layout.addWidget(self.strategy_list)
        self.strategy_tab.setLayout(layout)

    def show_strategy(self):
        import fastf1

        self.strategy_list.clear()
        if self.race_combo.count() == 0:
            return
        label = self.race_combo.currentText()
        season = int(self.season_combo.currentText())
        round_num = int(label.split(" ")[0][1:])
        session = fastf1.get_session(season, round_num, 'R')
        session.load()

        laps = session.laps
        if laps.empty:
            return

        for drv in session.drivers:
            dlaps = laps.pick_driver(drv)
            if dlaps.empty:
                continue
            code = session.get_driver(drv)["Abbreviation"]
            stints = dlaps["Compound"].groupby((dlaps["Compound"] != dlaps["Compound"].shift()).cumsum()).agg(
                ["first", "size"]
            )
            desc = ", ".join(f"{row['first']} x{row['size']}" for _, row in stints.iterrows())
            self.strategy_list.addItem(f"{code}: {desc}")

    # ---------- Pit Stops ----------
    def build_pitstop_tab(self):
        layout = QtWidgets.QVBoxLayout()
        self.pit_button = QtWidgets.QPushButton("Show Pit Stops")
        self.pit_button.clicked.connect(self.show_pitstops)
        self.pit_list = QtWidgets.QListWidget()
        layout.addWidget(self.pit_button)
        layout.addWidget(self.pit_list)
        self.pitstop_tab.setLayout(layout)

    def show_pitstops(self):
        import fastf1

        self.pit_list.clear()
        if self.race_combo.count() == 0:
            return
        label = self.race_combo.currentText()
        season = int(self.season_combo.currentText())
        round_num = int(label.split(" ")[0][1:])
        session = fastf1.get_session(season, round_num, 'R')
        session.load()

        pits = session.laps[session.laps["PitOutTime"].notna() | session.laps["PitInTime"].notna()]
        if pits.empty:
            return

        for drv in session.drivers:
            dlaps = pits.pick_driver(drv)
            if dlaps.empty:
                continue
            code = session.get_driver(drv)["Abbreviation"]
            for _, lap in dlaps.iterrows():
                self.pit_list.addItem(f"{code}: Lap {int(lap['LapNumber'])}")

    # ---------- Sector Comparison ----------
    def build_sector_tab(self):
        layout = QtWidgets.QVBoxLayout()
        self.sector_button = QtWidgets.QPushButton("Compare Sectors (Fastest Laps)")
        self.sector_button.clicked.connect(self.show_sector_comparison)
        self.sector_list = QtWidgets.QListWidget()
        layout.addWidget(self.sector_button)
        layout.addWidget(self.sector_list)
        self.sector_tab.setLayout(layout)

    def show_sector_comparison(self):
        import fastf1

        self.sector_list.clear()
        if self.race_combo.count() == 0:
            return
        label = self.race_combo.currentText()
        season = int(self.season_combo.currentText())
        round_num = int(label.split(" ")[0][1:])
        session = fastf1.get_session(season, round_num, 'R')
        session.load()

        laps = session.laps
        if laps.empty:
            return

        for drv in session.drivers:
            dlaps = laps.pick_driver(drv)
            if dlaps.empty:
                continue
            lap = dlaps.pick_fastest()
            code = session.get_driver(drv)["Abbreviation"]
            s1 = lap.get("Sector1Time", None)
            s2 = lap.get("Sector2Time", None)
            s3 = lap.get("Sector3Time", None)
            self.sector_list.addItem(f"{code}: S1={s1}, S2={s2}, S3={s3}")

    # ---------- Driver Stats (simple, per race) ----------
    def build_stats_tab(self):
        layout = QtWidgets.QVBoxLayout()
        self.stats_button = QtWidgets.QPushButton("Show Simple Driver Stats (this race)")
        self.stats_button.clicked.connect(self.show_driver_stats)
        self.stats_list = QtWidgets.QListWidget()
        layout.addWidget(self.stats_button)
        layout.addWidget(self.stats_list)
        self.stats_tab.setLayout(layout)

    def show_driver_stats(self):
        self.stats_list.clear()
        if self.race_combo.count() == 0:
            return
        idx = self.race_combo.currentIndex()
        race_id = self.races[idx]["race_id"]
        results = get_results_for_race(race_id)
        for r in results:
            code = r["driver_code"]
            pos = r["finish_position"]
            pts = r["points"]
            laps = r["laps_completed"]
            status = r["status"]
            self.stats_list.addItem(f"{code}: P{pos}, {pts} pts, {laps} laps, {status}")


def main():
    init_db()
    # debug_list_tables()
    # debug_race_results_columns()
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.resize(1200, 750)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()