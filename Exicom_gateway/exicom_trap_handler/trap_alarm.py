
def alarm_id_dict():


	alarm_dict = {0:{0:'lowFloat', 1:'lowLoad', 2:'highFloat', 3:'highLoad', 4:'rectifierFail', 5:'multipleRectifierFail',\
			6:'rectifierCommsLost',7:'multipleRectifierCommsLost',8:'partialAcFail',9:'acFail',10:'systemOverload',\
			11:'loadFuseFail',12:'batteryFuseFail',13:'batteryTestFail',14:'movFail',15:'acdFanFail',\
			16:'lvd1Disconnected',17:'lvd1Fail',18:'lvd1Manual',19:'lvd2Disconnected',20:'lvd2Fail',21:'lvd2Manual',\
			22:'batteryTemperatureLow',23:'batteryTemperatureHigh',24:'sensorFail',25:'equalize',26:'fastCharge',\
			27:'batteryTest',28:'auxiliarySensorFail',29:'inDischarge',30:'batteryCurrentLimit',31:'rectifierNoLoad',\
			32:'rectifierCurrentLimit',33:'rectifierOverTemperature',34:'acPhase1Fail',35:'acPhase1Voltage',\
			36:'acPhase2Fail',37:'acPhase2Voltage',38:'acPhase3Fail',39:'acPhase3Voltage',40:'acFrequency',41:'reserved',\
			42:'cabinetFanFail',43:'unmappedIobFound',44:'unknownHardware',45:'iobCommsLost',46:'standbyMode',\
			47:'lvd1CharacterizationError',48:'lvd2CharacterizationError',49:'stringFail',50:'generatorFail',\
			51:'lvdDisconnected',52:'lvdFail',53:'lvdManual',54:'lvdCharacterizationError',55:'configurationError',\
			56:'wrongBatteryPolarity',57:'characterizingBattery',58:'doManual',59:'normalCharge'},
		     1:{1: 'Analog_Input_High_1', 2: 'Analog_Input_High_2', 3: 'Analog_Input_High_3', 4: 'Analog_Input_High_4', \
			5: 'Analog_Input_High_5', 6: 'Analog_Input_High_6', 7: 'Analog_Input_High_7', 8: 'Analog_Input_High_8', \
			9: 'Analog_Input_High_9', 10: 'Analog_Input_High_10', 11: 'Analog_Input_High_11', 12:'Analog_Input_High_12',			      13: 'Analog_Input_High_13', 14: 'Analog_Input_High_14', 15: 'Analog_Input_High_15',\
			16: 'Analog_Input_High_16', 17: 'Analog_Input_High_17', 18: 'Analog_Input_High_18', \
			19: 'Analog_Input_High_19', 20: 'Analog_Input_High_20', 21: 'Analog_Input_High_21', \
			22: 'Analog_Input_High_22', 23: 'Analog_Input_High_23', 24: 'Analog_Input_High_24', \
			25: 'Analog_Input_High_25', 26: 'Analog_Input_High_26', 27: 'Analog_Input_High_27', \
			28: 'Analog_Input_High_28', 29: 'Analog_Input_High_29', 30: 'Analog_Input_High_30', \
			31: 'Analog_Input_High_31', 32: 'Analog_Input_High_32', 33: 'Analog_Input_High_33', \
			34: 'Analog_Input_High_34', 35: 'Analog_Input_High_35', 36: 'Analog_Input_High_36', \
			37: 'Analog_Input_High_37', 38: 'Analog_Input_High_38', 39: 'Analog_Input_High_39', \
			40: 'Analog_Input_High_40', 41: 'Analog_Input_High_41', 42: 'Analog_Input_High_42', \
			43: 'Analog_Input_High_43', 44: 'Analog_Input_High_44', 45: 'Analog_Input_High_45', \
			46: 'Analog_Input_High_46', 47: 'Analog_Input_High_47', 48: 'Analog_Input_High_48'},
		      2:{1: 'Analog_Input_low_1', 2: 'Analog_Input_low_2', 3: 'Analog_Input_low_3', 4: 'Analog_Input_low_4', \
		       	5: 'Analog_Input_low_5', 6: 'Analog_Input_low_6', 7: 'Analog_Input_low_7', 8: 'Analog_Input_low_8', \
			9: 'Analog_Input_low_9', 10: 'Analog_Input_low_10', 11: 'Analog_Input_low_11', 12: 'Analog_Input_low_12',\
			13: 'Analog_Input_low_13', 14: 'Analog_Input_low_14', 15: 'Analog_Input_low_15', 16: 'Analog_Input_low_16',\
			17: 'Analog_Input_low_17', 18: 'Analog_Input_low_18', 19: 'Analog_Input_low_19', 20: 'Analog_Input_low_20',\
			21: 'Analog_Input_low_21', 22: 'Analog_Input_low_22', 23: 'Analog_Input_low_23', 24: 'Analog_Input_low_24',\
			25: 'Analog_Input_low_25', 26: 'Analog_Input_low_26', 27: 'Analog_Input_low_27', 28: 'Analog_Input_low_28', \
                        29: 'Analog_Input_low_29', 30: 'Analog_Input_low_30', 31: 'Analog_Input_low_31', 32: 'Analog_Input_low_32', \
                        33: 'Analog_Input_low_33', 34: 'Analog_Input_low_34', 35: 'Analog_Input_low_35', 36: 'Analog_Input_low_36', \
                        37: 'Analog_Input_low_37', 38: 'Analog_Input_low_38', 39: 'Analog_Input_low_39', 40: 'Analog_Input_low_40',\
			41: 'Analog_Input_low_41', 42: 'Analog_Input_low_42', 43: 'Analog_Input_low_43', 44: 'Analog_Input_low_44', \
			45: 'Analog_Input_low_45', 46: 'Analog_Input_low_46', 47: 'Analog_Input_low_47', 48: 'Analog_Input_low_48'},
		     3:{1: 'Digital_Input_1', 2: 'Digital_Input_2', 3: 'Digital_Input_3', 4: 'Digital_Input_4', 5: 'Digital_Input_5'\
              		, 6: 'Digital_Input_6', 7: 'Digital_Input_7', 8: 'Digital_Input_8', 9: 'Digital_Input_9', \
			10: 'Digital_Input_10', 11: 'Digital_Input_11', 12: 'Digital_Input_12', 13: 'Digital_Input_13', 
			14: 'Digital_Input_14', 15: 'Digital_Input_15', 16: 'Digital_Input_16', 17: 'Digital_Input_17', 
			18: 'Digital_Input_18', 19: 'Digital_Input_19', 20: 'Digital_Input_20', 21: 'Digital_Input_21', \
			22: 'Digital_Input_22', 23: 'Digital_Input_23', 24: 'Digital_Input_24', 25: 'Digital_Input_25', \
			26: 'Digital_Input_26', 27: 'Digital_Input_27', 28: 'Digital_Input_28', 29: 'Digital_Input_29', \
			30: 'Digital_Input_30', 31: 'Digital_Input_31', 32: 'Digital_Input_32', 33: 'Digital_Input_33', \
			34: 'Digital_Input_34', 35: 'Digital_Input_35', 36: 'Digital_Input_36', 37: 'Digital_Input_37',\
		 	38: 'Digital_Input_38', 39: 'Digital_Input_39', 40: 'Digital_Input_40', 41: 'Digital_Input_41', \
			42: 'Digital_Input_42', 43: 'Digital_Input_43', 44: 'Digital_Input_44', 45: 'Digital_Input_45', \
			46: 'Digital_Input_46', 47: 'Digital_Input_47', 48: 'Digital_Input_48', 49: 'Digital_Input_49', \
			50: 'Digital_Input_50', 51: 'Digital_Input_51', 52: 'Digital_Input_52', 53: 'Digital_Input_53', \
			54: 'Digital_Input_54', 55: 'Digital_Input_55', 56: 'Digital_Input_56', 57: 'Digital_Input_57', \
			58: 'Digital_Input_58', 59: 'Digital_Input_59', 60: 'Digital_Input_60', 61: 'Digital_Input_61', \
			62: 'Digital_Input_62', 63: 'Digital_Input_63', 64: 'Digital_Input_64', 65: 'Digital_Input_65', \
			66: 'Digital_Input_66', 67: 'Digital_Input_67', 68: 'Digital_Input_68', 69: 'Digital_Input_69', \
			70: 'Digital_Input_70', 71: 'Digital_Input_71', 72: 'Digital_Input_72', 73: 'Digital_Input_73', \
			74: 'Digital_Input_74', 75: 'Digital_Input_75', 76: 'Digital_Input_76', 77: 'Digital_Input_77',\
			78: 'Digital_Input_78', 79: 'Digital_Input_79', 80: 'Digital_Input_80', 81: 'Digital_Input_81',\
			82: 'Digital_Input_82', 83: 'Digital_Input_83', 84: 'Digital_Input_84', 85: 'Digital_Input_85', \
			86: 'Digital_Input_86', 87: 'Digital_Input_87', 88: 'Digital_Input_88', 89: 'Digital_Input_89', \
			90: 'Digital_Input_90', 91: 'Digital_Input_91', 92: 'Digital_Input_92', 93: 'Digital_Input_93', \
			94: 'Digital_Input_94', 95: 'Digital_Input_95', 96: 'Digital_Input_96', 97: 'Digital_Input_97',\
			98: 'Digital_Input_98', 99: 'Digital_Input_99', 100: 'Digital_Input_100', 101: 'Digital_Input_101',\
			102: 'Digital_Input_102', 103: 'Digital_Input_103', 104: 'Digital_Input_104', 105: 'Digital_Input_105',\
		 	106: 'Digital_Input_106', 107: 'Digital_Input_107', 108: 'Digital_Input_108'},
		     4:{1:'Smart_alarm_1', 2:'Smart_alarm_2', 3:'Smart_alarm_3', 4:'Smart_alarm_4', 5:'Smart_alarm_5', \
			6:'Smart_alarm_6', 7:'Smart_alarm_7', 8:'Smart_alarm_8', 9:'Smart_alarm_9', 10:'Smart_alarm_10',\
			11:'Smart_alarm_11', 12:'Smart_alarm_12', 13:'Smart_alarm_13', 14:'Smart_alarm_14', 15:'Smart_alarm_15', \
			16:'Smart_alarm_16', 17:'Smart_alarm_17', 18:'Smart_alarm_18', 19:'Smart_alarm_19', 20:'Smart_alarm_20',\
			21:'Smart_alarm_21', 22:'Smart_alarm_22', 23:'Smart_alarm_23', 24:'Smart_alarm_24', 25:'Smart_alarm_25', \
			26:'Smart_alarm_26', 27:'Smart_alarm_27', 28:'Smart_alarm_28', 29:'Smart_alarm_29', 30:'Smart_alarm_30', \
			31:'Smart_alarm_31', 32:'Smart_alarm_32'}
			}

	return alarm_dict



