# app.py
import sys
from PyQt6 import QtWidgets, QtCore
from db import init_db, get_seasons, get_races_for_season, get_results_for_race


class ResultsTableModel(QtCore.QAbstractTableModel):
    def __init__(self, data, headers, parent=None):
        super().__init__(parent)
        self._data = data
        self._headers = headers

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            row = self._data[index.row()]
            key = self._headers[index.column()]
            return row.get(key)
        return None

    def headerData(self, section, orientation, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == QtCore.Qt.Orientation.Horizontal:
            return self._headers[section]
        return section + 1


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("F1 Stats Explorer")

        self.season_combo = QtWidgets.QComboBox()
        self.race_combo = QtWidgets.QComboBox()
        self.results_table = QtWidgets.QTableView()

        self._season_map = {}  # display -> season_id
        self._race_map = {}    # display -> race_id

        self._setup_layout()
        self._load_seasons()

        self.season_combo.currentIndexChanged.connect(self.on_season_changed)
        self.race_combo.currentIndexChanged.connect(self.on_race_changed)

    def _setup_layout(self):
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.addWidget(QtWidgets.QLabel("Season:"))
        top_layout.addWidget(self.season_combo)
        top_layout.addWidget(QtWidgets.QLabel("Race:"))
        top_layout.addWidget(self.race_combo)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.results_table)

        self.setLayout(main_layout)
        self.resize(900, 600)

    def _load_seasons(self):
        seasons = get_seasons()
        self.season_combo.clear()
        self._season_map.clear()

        for row in seasons:
            label = str(row["year"])
            self.season_combo.addItem(label)
            self._season_map[label] = row["season_id"]

        if seasons:
            self.season_combo.setCurrentIndex(0)
            self.on_season_changed(0)

    def on_season_changed(self, index):
        if index < 0:
            return
        label = self.season_combo.currentText()
        season_id = self._season_map.get(label)
        if not season_id:
            return

        races = get_races_for_season(season_id)
        self.race_combo.clear()
        self._race_map.clear()

        for row in races:
            label = f"R{row['round']:02d} - {row['name']}"
            self.race_combo.addItem(label)
            self._race_map[label] = row["race_id"]

        if races:
            self.race_combo.setCurrentIndex(0)
            self.on_race_changed(0)

    def on_race_changed(self, index):
        if index < 0:
            return
        label = self.race_combo.currentText()
        race_id = self._race_map.get(label)
        if not race_id:
            return

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

        model = ResultsTableModel(data, headers, self)
        self.results_table.setModel(model)
        self.results_table.resizeColumnsToContents()


def main():
    init_db()  # safe if already created
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()