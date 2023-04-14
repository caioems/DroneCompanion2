import pathlib
from tkinter import Tk
from tkinter.filedialog import askdirectory

class LogList:
    def __init__(self):
      self.root_folder = self.input_window()
      self.log_list = self.create_log_list(self.root_folder)
      
    def input_window(self):
      root = Tk()
      root.update()
      path = askdirectory(title='Select the root folder:')
      root.destroy()
      return path
    
    def create_log_list (self, root_folder):
      log_list = list(pathlib.Path(root_folder).glob(r"**\*.BIN"))
      return log_list 
    
# a = LogList()
# print(a)
    
    