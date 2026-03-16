# app.py
import sys
from PyQt6 import QtWidgets, QtCore
from db import init_db, get_seasons, get_races_for_season, get_results_for_race


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

        self.season_combo = QtWidgets.QComboBox()
        self.race_combo = QtWidgets.QComboBox()
        self.table = QtWidgets.QTableView()

        self._season_map = {}
        self._race_map = {}

        # Tabs
        self.tabs = QtWidgets.QTabWidget()
        self.results_tab = QtWidgets.QWidget()
        self.lapchart_tab = QtWidgets.QWidget()
        self.telemetry_tab = QtWidgets.QWidget()

        self.tabs.addTab(self.results_tab, "Results")
        self.tabs.addTab(self.lapchart_tab, "Lap Chart")
        self.tabs.addTab(self.telemetry_tab, "Telemetry")

        # Top controls
        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("Season:"))
        top.addWidget(self.season_combo)
        top.addWidget(QtWidgets.QLabel("Race:"))
        top.addWidget(self.race_combo)

        # Results tab layout
        res_layout = QtWidgets.QVBoxLayout()
        res_layout.addLayout(top)
        res_layout.addWidget(self.table)
        self.results_tab.setLayout(res_layout)

        # Build other tabs
        self.build_lapchart_tab()
        self.build_telemetry_tab()

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

        self.load_seasons()

        self.season_combo.currentIndexChanged.connect(self.on_season_changed)
        self.race_combo.currentIndexChanged.connect(self.on_race_changed)
        self.table.clicked.connect(self.on_driver_clicked)

    # -------------------------
    # Load seasons and races
    # -------------------------
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

    def on_season_changed(self, index):
        if index < 0:
            return

        label = self.season_combo.currentText()
        season_id = self._season_map[label]

        races = get_races_for_season(season_id)
        self.race_combo.clear()
        self._race_map.clear()

        for r in races:
            lbl = f"R{r['round']:02d} - {r['name']}"
            self.race_combo.addItem(lbl)
            self._race_map[lbl] = r["race_id"]

        if races:
            self.on_race_changed(0)

    def on_race_changed(self, index):
        if index < 0:
            return

        label = self.race_combo.currentText()
        race_id = self._race_map[label]

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

        # Populate telemetry driver lists
        self.driver1_combo.clear()
        self.driver2_combo.clear()

        for r in results:
            code = r["driver_code"]
            if code:
                self.driver1_combo.addItem(code)
                self.driver2_combo.addItem(code)

    # -------------------------
    # Driver click → popup
    # -------------------------
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

    # -------------------------
    # Lap Chart Tab
    # -------------------------
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

    # -------------------------
    # Telemetry Tab
    # -------------------------
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


def main():
    init_db()
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.resize(1100, 700)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()