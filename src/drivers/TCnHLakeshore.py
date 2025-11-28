#TCLakeshoreDemo
#LakeShore 335 Temperature Controller
#This script just read the temperature values




#import csv
from lakeshore import Model335, Model335InputSensorSettings
from time import sleep
from PyQt5 import QtCore
from collections import defaultdict


class TCnHLakeshore(QtCore.QThread):


    name = 'tc'


    temperature_updated=QtCore.pyqtSignal(dict)


    def __init__(self):


        super(TCnHLakeshore,self).__init__()




       
        try:
            #Communication with the device
            self.my_model_335 = Model335(57600)


            #Set the sensor parameters
            self.sensor_settings = Model335InputSensorSettings(self.my_model_335.InputSensorType.DIODE, True, False,
                                              self.my_model_335.InputSensorUnits.KELVIN,
                                              self.my_model_335.DiodeRange.TWO_POINT_FIVE_VOLTS)
           
            # Apply settings to input A of the instrument
            self.my_model_335.set_input_sensor("A", self.sensor_settings)
            self.my_model_335.set_input_sensor("B", self.sensor_settings)


            # Set diode excitation current on channel A to 10uA
            self.my_model_335.set_diode_excitation_current("A", self.my_model_335.DiodeCurrent.TEN_MICROAMPS)
            self.my_model_335.set_diode_excitation_current("B", self.my_model_335.DiodeCurrent.TEN_MICROAMPS)


            #Get the temperature values, 0 element is the sample one.
            self.temperature_reading = self.my_model_335.get_all_kelvin_reading()


           
        except:
            print("COM not connected")
            self.my_model_335=None
            self.temperature_reading = [0, 0]


        self.parameter_display_dict = {}


        # setting up variables, open array
        self.set_T = []
        self.current_T = []
        self.stop = False


        #Values of the temperature A (the sample one)
        self.parameter_display_dict['TempA'] = {}
        self.parameter_display_dict['TempA']['val'] = self.temperature_reading[0]
        self.parameter_display_dict['TempA']['unit'] = 'K'
        self.parameter_display_dict['TempA']['max'] = 350
        self.parameter_display_dict['TempA']['min'] = 1
        self.parameter_display_dict['TempA']['read'] = True


        #Values of the temperature B (non sample one)
        self.parameter_display_dict['TempB'] = {}
        self.parameter_display_dict['TempB']['val'] = self.temperature_reading[1]
        self.parameter_display_dict['TempB']['unit'] = 'K'
        self.parameter_display_dict['TempB']['max'] = 350
        self.parameter_display_dict['TempB']['min'] = 1
        self.parameter_display_dict['TempB']['read'] = True


        #Values of the setpoint
        self.parameter_display_dict['SetPoint'] = {}
        self.parameter_display_dict['SetPoint']['val'] = 270
        self.parameter_display_dict['SetPoint']['unit'] = 'K'
        self.parameter_display_dict['SetPoint']['max'] = 350
        self.parameter_display_dict['SetPoint']['min'] = 1
        self.parameter_display_dict['SetPoint']['read'] = False


        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']


        # defining waitTime
        self.waitTime = 0.1


        # start updating temp
        self.UpdateWorker = UpdateWorker(self.my_model_335)
        self.UpdateWorker.new_T.connect(self.update_temp)
        self.UpdateWorker.start()








    def set_parameter(self, param, value):


        if param == 'TempA':
            temp=self.my_model_335.get_all_kelvin_reading()
            self.parameter_dict['TempA'] = temp[0]
           
        if param == 'TempB':
            temp=self.my_model_335.get_all_kelvin_reading()
            self.parameter_dict['TempB'] = temp[1]
           
        if param == 'SetPoint':
            self.heater_control(self.parameter_dict['SetPoint'])




        if param in self.parameter_dict:
            self.parameter_dict[param] = value
            if param in self.parameter_display_dict:
                self.parameter_display_dict[param]['val'] = value
            print(f"Updated {param} to {value}")
        else:
            print(f"Parameter {param} not found in TCLakeshoreDemo")




        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']


        self.running = True


    def update_temp(self, new_T):
        self.parameter_dict['TempA'] = new_T[0]
        self.parameter_dict['TempB'] = new_T[1]






    #this function controls the heater


    def heater_control(self,set_point):


       
        #Entablish setpoint
        #self.set_point = 267


        #We are using heater 1 which resistance is 25omh, and we are applying current of 0.5A.
        self.my_model_335.set_heater_setup_one(self.my_model_335.HeaterResistance.HEATER_25_OHM, 0.5, self.my_model_335.HeaterOutputDisplay.POWER) #MAX CURRENT 0.7A


        #Gives the set point information to the heater 1
        self.my_model_335.set_control_setpoint(1, set_point)






        #The heater is giving LOW power (it could be MEDIUM or HIGH)
        self.my_model_335.set_heater_range(1, self.my_model_335.HeaterRange.MEDIUM)




        #HEATER 1 WITH TEMP A
        self.my_model_335.set_heater_output_mode(
            1,                                  # Heater output 1
            self.my_model_335.HeaterOutputMode.CLOSED_LOOP,  # Closed Loop
            self.my_model_335.InputSensor.CHANNEL_A,         # Temperature channel A
            powerup_enable=False                )


            ######################################################################################################################################### AUTOTUNE
            #########################################################################################################################################
            # AUTOTUNE LOOP ROBUSTO: REINTENTAR HASTA QUE FUNCIONE
            #########################################################################################################################################


        self.tempA = []
        self.tempB = []
        self.heater1 = []


        try:
                while True:     # Este loop reinicia todo el control si algo falla
                    print("\n=== Intentando iniciar AUTOTUNE ===")


                    try:
                        #
                        # 1. Verificar condiciones antes de iniciar autotune
                        #
                        while True:
                            heater_error = self.my_model_335.get_heater_status(1)
                            if heater_error is not self.my_model_335.HeaterError.NO_ERROR:
                                raise Exception(f"Heater error: {heater_error.name}")


                            kelvin_reading = self.my_model_335.get_kelvin_reading(1)
                            if abs(kelvin_reading - self.s_p) > 5:
                                raise Exception("Temperatura fuera del rango ±5 K para iniciar autotune")


                            # Si todo bien → iniciar autotune
                            self.my_model_335.set_autotune(1, self.my_model_335.AutotuneMode.P_I)
                            print("Autotune iniciado correctamente!")
                            break  # salir del pre-check


                        #
                        # 2. Monitorear el autotune hasta que termine o ocurra un error
                        #
                        while True:
                            autotune_status = self.my_model_335.get_tuning_control_status()


                            if autotune_status["tuning_error"]:
                                raise Exception("Autotune reportó un error interno")


                            if not autotune_status["active_tuning_enable"]:
                                print("Autotune finalizado exitosamente!")
                                break


                            print(f"Stage: {autotune_status['stage_status']} / 10")


                            # Registrar datos
                            temperature_reading = self.my_model_335.get_all_kelvin_reading()
                            heater_output_1 = self.my_model_335.get_heater_output(1)


                            self.tempA.append(temperature_reading[0])
                            self.tempB.append(temperature_reading[1])
                            self.heater1.append(heater_output_1)


                            sleep(5)


                        # Si llegamos aquí, el autotune terminó sin errores
                        break


                    except Exception as e:
                        print("\n*** ERROR detectado durante autotune ***")
                        print("Detalle:", e)


                        # Reiniciar heater y control
                        self.my_model_335.all_heaters_off()
                        sleep(0.5)
                        self.my_model_335.set_manual_output(1, 0)
                        sleep(0.5)
                        self.my_model_335.set_heater_range(1, self.my_model_335.HeaterRange.MEDIUM)


                        print("Reintentando en 3 segundos...\n")
                        sleep(3)
                        continue  # vuelve a intentar el autotune


                #####################################################################################################
                # 3. CONTROL NORMAL POST-AUTOTUNE
                #####################################################################################################


                print("\n=== Control corriendo después de autotune ===")


                while True:
                    temperature_reading = self.my_model_335.get_all_kelvin_reading()
                    heater_output_1 = self.my_model_335.get_heater_output(1)


                    self.tempA.append(temperature_reading[0])
                    self.tempB.append(temperature_reading[1])
                    self.heater1.append(heater_output_1)


                    print(f"Temp A = {temperature_reading[0]:.3f} K")
                    print(f"Temp B = {temperature_reading[1]:.3f} K")
                    print(f"Heater = {heater_output_1}%")


                    if abs(temperature_reading[0] - self.set_point) > 5:
                        #print("Temperatura fuera de rango. Apagando heater...")
                        #my_model_335.all_heaters_off()
                        #break
                        raise Exception


                    sleep(5)


                #####################################################################################################
                # GUARDAR LOG AL FINAL
                #####################################################################################################


                with open(r"C:\Users\Andres Sanchez\Downloads\log_lakeshore.csv", "w", newline="") as f:
                    self.writer = self.csv.writer(f)
                    self.writer.writerow(["TempA (K)", "TempB (K)", "Heater (%)"])
                    for a, b, h in zip(self.tempA, self.tempB, self.heater1):
                        self.writer.writerow([a, b, h])


                print("log_lakeshore.csv guardado correctamente")


        except KeyboardInterrupt:
                print("\nInterrupción por usuario. Guardando datos...")


                with open(r"C:\Users\Andres Sanchez\Downloads\log_lakeshore.csv", "w", newline="") as f:
                    self.writer = self.csv.writer(f)
                    self.writer.writerow(["TempA (K)", "TempB (K)", "Heater (%)"])
                    for a, b, h in zip(self.tempA, self.tempB, self.heater1):
                        self.writer.writerow([a, b, h])


                self.my_model_335.all_heaters_off()
                print("Heaters OFF y archivo guardado.")








class UpdateWorker(QtCore.QThread):
    new_T = QtCore.pyqtSignal(list)


    def __init__(self, model):
        super(UpdateWorker, self).__init__()
    #    self.currentT = []
        self.stop = False
        self.waitTime = 0.1
        self.my_model_335 = model
        #self.target = 300


    def run(self):
        while not self.stop:
            # calling the read temperature function
            self.readtemp = self.my_model_335.get_all_kelvin_reading()


            # waiting to remeasure the temperature
            sleep(self.waitTime)
            self.new_T.emit(self.readtemp)


    #def read_T(self):
        # read the current platform target temperature
    #    temps=self.my_model_335.get_all_temepratures()
    #    tempa=temps[0]
    #    tempb=temps[1]
    #    return tempa



