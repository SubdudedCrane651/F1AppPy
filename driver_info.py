# driver_info.py
import requests
from PyQt6 import QtWidgets, QtGui, QtCore


class DriverInfoWindow(QtWidgets.QWidget):
    def __init__(self, session, driver_code, driver_name, team_name, season):
        super().__init__()
        self.setWindowTitle(driver_name)
        self.resize(500, 700)

        layout = QtWidgets.QVBoxLayout()

        # Title labels
        self.driver_label = QtWidgets.QLabel(driver_name)
        self.driver_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.driver_label.setStyleSheet("font-size: 22px; font-weight: bold;")

        self.team_label = QtWidgets.QLabel(team_name)
        self.team_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.team_label.setStyleSheet("font-size: 16px;")

        # Image containers
        self.driver_img = QtWidgets.QLabel()
        self.driver_img.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.driver_img.setFixedHeight(260)   # <--- HARD LIMIT

        self.car_img = QtWidgets.QLabel()
        self.car_img.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.car_img.setFixedHeight(220)      # <--- HARD LIMIT

        layout.addWidget(self.driver_label)
        layout.addWidget(self.team_label)
        layout.addWidget(self.driver_img)
        layout.addWidget(self.car_img)

        self.setLayout(layout)

        self.load_images(session, driver_code, team_name, season)

    def load_images(self, session, driver_code, team_name, season):
        drv = session.get_driver(driver_code)

        # FastF1 driver portrait
        driver_url = drv.get("HeadshotUrl", None)

        # F1.com car image (reliable)
        team_slug = team_name.replace(" ", "-").lower()
        car_url = f"https://www.formula1.com/content/dam/fom-website/teams/{season}/{team_slug}.png"

        self.set_image(self.driver_img, driver_url)
        self.set_image(self.car_img, car_url)

    def set_image(self, label, url):
        if not url:
            label.setText("Image not available")
            return

        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                pix = QtGui.QPixmap()
                pix.loadFromData(resp.content)

                # Scale to fit inside the fixed-height label
                scaled = pix.scaled(
                    label.width(),
                    label.height(),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation
                )

                label.setPixmap(scaled)
            else:
                label.setText("Image not available")
        except:
            label.setText("Image not available")