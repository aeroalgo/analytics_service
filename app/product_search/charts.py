from pydantic import BaseModel, Field
from typing import List

class LineChartData(BaseModel):
    """Класс данных для линейного графика"""
    label: str
    data: List[float] = Field(default=[])
    backgroundColor: str = Field(default='transparent')
    borderColor: str = Field(default='rgba(220,53,69,0.75)')
    borderWidth: int = Field(default=3)
    pointStyle: str = Field(default='circle')
    pointRadius: int = Field(default=3)
    pointBorderColor: str = Field(default='transparent')
    pointBackgroundColor: str = Field(default='rgba(220,53,69,0.75)')

    def set_color(self, idx: int):
        color_magazine = {
            0: "rgba(174, 221, 125, 0.9)",  # Зеленый
            1: "rgba(95,222,112, 0.9)",  # Фиолетовый
            2: "rgba(138, 180, 255, 0.9)",  # Синий
            3: "rgba(168, 228, 252, 0.9)",
            4: "rgba(255, 235, 149, 0.9)",
            5: "rgba(252, 162, 102, 0.9)",
            6: "rgba(254, 140, 140, 0.9)",
            7: "rgba(167, 148, 255, 0.9)",
            8: "rgba(252, 198, 126, 0.9)",
        }
        self.borderColor = color_magazine.get(idx)
        self.pointBackgroundColor = color_magazine.get(idx)
