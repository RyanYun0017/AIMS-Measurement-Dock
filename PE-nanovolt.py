import pyvisa
from sentio_prober_control.Communication.CommunicatorGpib import *
from sentio_prober_control.Sentio.ProberSentio import *
from pymeasure.instruments.keithley import Keithley2450
import numpy as np
import pandas as pd
from time import sleep


class CustomCommunicatorGpib(CommunicatorGpib):
   def __init__(self, vendor, address):
       super().__init__(vendor)
       self.address = address
       self.rm = pyvisa.ResourceManager()
       self.instrument = self.rm.open_resource(self.address)
   def set_timeout(self, timeout_ms):
       self.instrument.timeout = timeout_ms
   def send(self, command):
       self.instrument.write(command)
   def read_line(self):
       return self.instrument.read()
def main():
   try:
       # Create the custom communicator with National Instruments card
       comm = CustomCommunicatorGpib(GpibCardVendor.NationalInstruments, "GPIB0::13::INSTR")
       # Set the timeout period (example: 10000 ms = 10 seconds)
       comm.set_timeout(10000) # Timeout is set in milliseconds
       # Initialize SentioProber with the communicator
       prober = SentioProber(comm)
       # Send an identification query to the instrument
       comm.send("*IDN?")
       response = comm.read_line()
       print("Instrument ID: {0}".format(response))
       # Create connection with SMU and test connection
       rm =pyvisa.ResourceManager()
       SMU = rm.open_resource('GPIB0::18::INSTR')
       nVolt = rm.open_resource('GPIB0::6::INSTR')
       # Reset the instrument and configure it for the IV sweep

       # Configure the SMU as a current source
       SMU.write('*RST')  # Reset the instrument
       SMU.write('SOUR:FUNC CURR')  # Set the source function to current
       SMU.write('SOUR:CURR:RANG 20E-6')  # Set the current range to 20 µA
       SMU.write('SENS:FUNC "VOLT"')  # Set the sense function to voltage
       SMU.write('SENS:VOLT:RANG 20E-3')  # Set the voltage range to 10 mV
       SMU.write('SENS:VOLT:NPLC 1')
       SMU.write('OUTP ON')  # Enable the outputv
       # Configure the nanovoltmeter
       nVolt.write('*RST')  # Reset the instrument
       nVolt.write('CONF:VOLT:DC 10E-3')  # Set measurement function to DC voltage, 10 mV range

       current_positive = 100e-6  # Positive current: 100 µA
       current_negative = -100e-6  # Negative current: -100 µA
       num_cycles = 10  # Number of cycles to alternate between currents

       start_current = -100e-6  # Start current: -100 µA
       stop_current = 100e-6  # Stop current: 100 µA
       num_points = 20  # Number of sweep points
       iv_sweep_currents = np.linspace(start_current, stop_current, num_points)

       delta_sweep_currents = []
       for i in range(100, 0, -5):
           delta_sweep_currents.extend([i, -i])
       delta_sweep_currents.append(0)  # Add the 0 current at the end
       delta_sweep_currents = [current * 1e-6 for current in delta_sweep_currents]



       landing_count= 1


       # Move to the first Die then iterate through all the subsite

       for l in range(1,landing_count+1):
            try:
                print(f'{l} times landing Started')
                #col, row, site = prober.map.step_first_die()
                col,row,site = prober.map.step_die(1,0,81)
                bin_value = 0
                prober.move_chuck_contact()
                print("Moved to contact on first die")
                sleep(0.3)
                # Perform the delta mode measurement
                data = []
                #print(delta_sweep_currents)
                for current in delta_sweep_currents:
                        SMU.write(f'SOUR:CURR {current}')  # Set the current
                        sleep(0.1)  # Wait for settling time
                        voltage = nVolt.query('READ?')  # Read the voltage from the nanovoltmeter
                        data.append((current, float(voltage)))  # Store the current and voltage
                df = pd.DataFrame(data, columns=['Current (A)', 'Voltage (V)'])
                filename = f'Sweep_Voltage_{col}_{row}_{site}_{l}.csv'
                df.to_csv(filename, index=False)
                print(f'Measurement done for position {col}, {row} (Site: {site}).')



                #filename = f"{col}{row}{site}{l}_landing.jpg"
                #prober.vision.snap_image(file=filename,where =1 )
                #print("Screenshot taken")

                prober.move_chuck_separation()
                print("Frsit die sepration")
                """ prober.map.step_die(2,1,2)
                bin_value = 0 """
                while True:
                    col, row, site = prober.map.subsites.bin_step_next(bin_value)
                    print(f'Position {col}, {row} (Site: {site})')
                    sleep(0.3)
                    prober.move_chuck_contact()
                    print("Moved to contact")
                    sleep(0.3)
                    bin_value = 0 if site == 0 else bin_value + 1
                    # Run multiple time IV-Sweep if needed. If not, set k = 1

                    data = []

                    for current in delta_sweep_currents:
                        SMU.write(f'SOUR:CURR {current}')  # Set the current
                        sleep(0.1)  # Wait for settling time
                        voltage = nVolt.query('READ?')  # Read the voltage from the nanovoltmeter
                        data.append((current, float(voltage)))  # Store the current and voltage
                    df = pd.DataFrame(data, columns=['Current (A)', 'Voltage (V)'])
                    filename = f'Sweep_Voltage_{col}_{row}_{site}_{l}.csv'
                    df.to_csv(filename, index=False)
                    
                    print(f'Measurement done for position {col}, {row} (Site: {site}).')

                    #filename = f"{col}-{row}-{site}-{l}_landing.jpg"
                    #prober.vision.snap_image(file=filename,where =1 )
                    #print("Screenshot taken")

                    prober.move_chuck_separation()
                    print("Moved to Sepration")
                    print("Continuing stepping")
                
            except ProberException as e:
                # An end of route error is normal with this workflow.
                # Everything else will terminate the loop
                if e.error() != 11:
                    raise

   except pyvisa.VisaIOError as visa_err:
       print("\n#### VISA Error ##################################")
       print("VISA Error: {0}".format(visa_err))
   except Exception as e:
       print("\n#### Error ##################################")
       print("Exception: {0}".format(e))
if __name__ == "__main__":
   main()