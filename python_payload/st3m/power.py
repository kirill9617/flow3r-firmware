import machine
import time
import math
import sys_kernel


class Power:
    """
    Collects information about the power state (e.g. battery voltage) of the badge.

    Member of st3m.input.InputState, should be acquired from there, not instantiated manually.
    """

    def __init__(self) -> None:
        self._adc_pin = machine.Pin(9, machine.Pin.IN)
        self._adc = machine.ADC(self._adc_pin, atten=machine.ADC.ATTN_11DB)
        self._battery_voltage = self._battery_voltage_sample()
        self._battery_percentage = self._approximate_battery_percentage()
        self._ts = time.ticks_ms()

    def _battery_voltage_sample(self) -> float:
        return self._adc.read_uv() * 2 / 1e6

    def _update(self) -> None:
        ts = time.ticks_ms()
        if ts >= self._ts + 3000:
            # Sampling takes time, don't do it too often
            self._battery_voltage = self._battery_voltage_sample()
            self._battery_percentage = self._approximate_battery_percentage()
            self._ts = ts

    @property
    def battery_voltage(self) -> float:
        self._update()
        return self._battery_voltage

    @property
    def battery_charging(self) -> bool:
        """
        True if the battery is currently being charged.
        """
        return sys_kernel.battery_charging()

    @property
    def battery_percentage(self) -> int:
        self._update()
        return self._battery_percentage
    
    def _approximate_battery_percentage(self) -> int:
        """
        Returns approximate battery percentage ([0,100]) based on battery voltage
        (in volts).
        """
        # read battery voltage several times and average
        voltage = sum(self._battery_voltage_sample() for _ in range(10)) / 10
        print(voltage)

        if voltage > 4.16:
            return 100
        # LUT created from Joulescope measurement of "official" 2Ah Battery at 650mW discharge at 26°C and decimated from ~42k samples 
        batLUT = [
            (99, 4.150),
            (99, 4.1132),
            (98, 4.1054),
            (98, 4.0983),
            (97, 4.0915),
            (97, 4.0853),
            (97, 4.0792),
            (96, 4.0733),
            (96, 4.0677),
            (95, 4.0622),
            (95, 4.0568),
            (95, 4.0515),
            (94, 4.0461),
            (94, 4.0415),
            (93, 4.0367),
            (93, 4.0317),
            (93, 4.0271),
            (92, 4.0225),
            (92, 4.0179),
            (91, 4.0130),
            (91, 4.0087),
            (91, 4.0040),
            (90, 3.9994),
            (90, 3.9951),
            (89, 3.9907),
            (89, 3.9858),
            (89, 3.9817),
            (88, 3.9772),
            (88, 3.9728),
            (87, 3.9684),
            (87, 3.9640),
            (87, 3.9597),
            (86, 3.9553),
            (86, 3.9509),
            (85, 3.9465),
            (85, 3.9424),
            (85, 3.9380),
            (84, 3.9337),
            (84, 3.9288),
            (83, 3.9250),
            (83, 3.9207),
            (82, 3.9163),
            (82, 3.9121),
            (82, 3.9077),
            (81, 3.9034),
            (81, 3.8990),
            (80, 3.8949),
            (80, 3.8903),
            (80, 3.8860),
            (79, 3.8818),
            (79, 3.8778),
            (78, 3.8732),
            (78, 3.8692),
            (77, 3.8649),
            (77, 3.8607),
            (77, 3.8564),
            (76, 3.8521),
            (76, 3.8482),
            (75, 3.8440),
            (75, 3.8400),
            (75, 3.8360),
            (74, 3.8321),
            (74, 3.8279),
            (73, 3.8238),
            (73, 3.8196),
            (73, 3.8160),
            (72, 3.8118),
            (72, 3.8082),
            (71, 3.8044),
            (71, 3.8005),
            (71, 3.7966),
            (70, 3.7929),
            (70, 3.7889),
            (69, 3.7852),
            (69, 3.7815),
            (68, 3.7776),
            (68, 3.7739),
            (68, 3.7700),
            (67, 3.7665),
            (67, 3.7630),
            (66, 3.7593),
            (66, 3.7557),
            (66, 3.7520),
            (65, 3.7485),
            (65, 3.7450),
            (64, 3.7414),
            (64, 3.7378),
            (64, 3.7344),
            (63, 3.7309),
            (63, 3.7273),
            (62, 3.7239),
            (62, 3.7204),
            (62, 3.7171),
            (61, 3.7135),
            (61, 3.7102),
            (60, 3.7070),
            (60, 3.7036),
            (60, 3.7005),
            (59, 3.6972),
            (59, 3.6941),
            (58, 3.6907),
            (58, 3.6875),
            (58, 3.6845),
            (57, 3.6809),
            (57, 3.6782),
            (56, 3.6751),
            (56, 3.6721),
            (56, 3.6690),
            (55, 3.6660),
            (55, 3.6633),
            (54, 3.6601),
            (54, 3.6573),
            (54, 3.6541),
            (53, 3.6516),
            (53, 3.6488),
            (52, 3.6463),
            (52, 3.6434),
            (52, 3.6412),
            (51, 3.6388),
            (51, 3.6361),
            (51, 3.6340),
            (50, 3.6316),
            (50, 3.6295),
            (49, 3.6272),
            (49, 3.6251),
            (49, 3.6232),
            (48, 3.6211),
            (48, 3.6192),
            (47, 3.6173),
            (47, 3.6121),
            (46, 3.6104),
            (46, 3.6080),
            (46, 3.6065),
            (45, 3.6050),
            (45, 3.6048),
            (45, 3.6032),
            (44, 3.6017),
            (44, 3.6002),
            (43, 3.5985),
            (43, 3.5972),
            (43, 3.5958),
            (42, 3.5943),
            (42, 3.5928),
            (41, 3.5915),
            (41, 3.5896),
            (41, 3.5886),
            (40, 3.5874),
            (40, 3.5861),
            (39, 3.5847),
            (39, 3.5833),
            (39, 3.5821),
            (38, 3.5808),
            (38, 3.5795),
            (37, 3.5766),
            (37, 3.5753),
            (37, 3.5741),
            (36, 3.5725),
            (36, 3.5708),
            (35, 3.5700),
            (35, 3.5684),
            (35, 3.5670),
            (34, 3.5658),
            (34, 3.5646),
            (33, 3.5632),
            (33, 3.5621),
            (33, 3.5605),
            (32, 3.5619),
            (32, 3.5592),
            (31, 3.5573),
            (31, 3.5554),
            (31, 3.5536),
            (30, 3.5523),
            (30, 3.5509),
            (30, 3.5492),
            (29, 3.5480),
            (29, 3.5459),
            (28, 3.5450),
            (28, 3.5435),
            (28, 3.5418),
            (27, 3.5404),
            (27, 3.5389),
            (26, 3.5371),
            (26, 3.5358),
            (26, 3.5342),
            (25, 3.5328),
            (25, 3.5310),
            (24, 3.5293),
            (24, 3.5276),
            (24, 3.5256),
            (23, 3.5242),
            (23, 3.5227),
            (23, 3.5203),
            (22, 3.5183),
            (22, 3.5166),
            (21, 3.5149),
            (21, 3.5129),
            (21, 3.5110),
            (20, 3.5087),
            (20, 3.5066),
            (19, 3.5044),
            (19, 3.5022),
            (19, 3.4994),
            (18, 3.4976),
            (18, 3.4950),
            (18, 3.4926),
            (17, 3.4899),
            (17, 3.4874),
            (16, 3.4849),
            (16, 3.4821),
            (16, 3.4793),
            (15, 3.4765),
            (15, 3.4735),
            (15, 3.4701),
            (14, 3.4669),
            (14, 3.4636),
            (13, 3.4607),
            (13, 3.4572),
            (13, 3.4537),
            (12, 3.4499),
            (12, 3.4467),
            (11, 3.4431),
            (11, 3.4393),
            (11, 3.4352),
            (10, 3.4312),
            (10, 3.4271),
            (10, 3.4226),
            (9, 3.4184),
            (9, 3.4142),
            (8, 3.4095),
            (8, 3.4049),
            (8, 3.3997),
            (7, 3.3946),
            (7, 3.3901),
            (7, 3.3851),
            (6, 3.3803),
            (6, 3.3752),
            (5, 3.3698),
            (5, 3.3642),
            (5, 3.3578),
            (4, 3.3507),
            (4, 3.3425),
            (4, 3.3336),
            (3, 3.3228),
            (3, 3.3096),
            (2, 3.2930),
            (2, 3.2737),
            (2, 3.2501),
            (1, 3.2216),
            (1, 3.1862),
            (1, 3.1442),
            (0, 3.0938),
            (0, 3.0319),
            (0, 2.9592),
            (0, 0),
        ]
        
        #select percentage based on voltage reading and LUT
        for i in range(len(batLUT)):
            if voltage >= batLUT[i][1]:
                return batLUT[i][0]
        



