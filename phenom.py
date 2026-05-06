from tkinter import *
from PIL import ImageTk, ImageOps, ImageDraw, ImageFont
import PIL.Image
import pandas as pd
import numpy as numpy
import glob
import os
from tkinter import filedialog
from tkinter import ttk
from periodictable import elements
import pytesseract
from fontTools import ttLib

pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
custom_config = r'-l grc+eng --psm 1' # Greek (for mu and nu letters) and English (for m (metre))


class App(Tk):
    def __init__(self, title, size):

        #main setup
        super().__init__()
        self.title = title
        self.geometry(f'{size[0]}x{size[1]}')
        self.minsize(size[0],size[1])

        #getting fonts
        self.get_fonts()

        #widgets
        self.ImageOptions = ImageOptions(self)
        self.ImageOptions.place(relx=0.7,rely=0, relheight =0.9)

        self.preview = Preview(self)
        self.preview.place(relx=0.4, rely=0, relwidth=0.3, relheight= 0.3)

        self.options = Options(self, name = 'Project', preview_image = self.preview.preview_image,
                               options = self.ImageOptions.get_options,
                               text_pos = self.preview)
        
        self.options.place(relwidth=0.4, relx =0, rely =0, relheight=0.3)

        self.grid = Grid_Frame(self)
        self.grid.place(relwidth=0.7, relheight=0.7, relx=0, rely=0.3)


        

        #run
        self.mainloop()

    
    def get_fonts(self):
        path = r'.\fonts'
        global font_families

        font_families = { }
        fonts = os.listdir(path)
        for font in fonts:
            type_dict = { }
            if '.TTF' in font or '.ttf' in font:
                font_path = os.path.join(path, font)
                tmp = ttLib.TTFont(os.path.join(path,font))
                fontFamilyName = tmp['name'].getDebugName(1)
                font_type = tmp['name'].getDebugName(2)
                type_dict = {font_type: font_path}
                
                if fontFamilyName not in font_families.keys():
                    font_families[fontFamilyName] = type_dict
                else:
                    font_families[fontFamilyName].update(type_dict)

        return font_families

    

class Options(LabelFrame):
    
    def __init__(self, parent, name, **kwargs):

        #Options frame setup
        super().__init__(parent)
        self.configure(text=name)
        self.create_widgets()
        self.preview_im = kwargs['preview_image']
        self.test = kwargs['options']
        self.text_position = kwargs['text_pos']
        self.selected = None

    def create_widgets(self):

        Button(self, text = 'Select project', command = self.project_selection).grid(row=0, column =0)

        Label(self, text = 'SEM images').grid(row=1, column =0)
        self.photos_box = Listbox(self)
        self.photos_box.grid(row=2, column = 0)
        self.photos_box.bind('<<ListboxSelect>>', self.preview)

        Label(self, text = 'Analyses').grid(row=1, column =1)
        self.maps_folders = Listbox(self)
        self.maps_folders.grid(row=2, column =1)
        self.maps_folders.bind('<<ListboxSelect>>', self.show_maps)
        
        Label(self, text = 'EDS maps').grid(row=1, column =2)
        self.maps_box = Listbox(self)
        self.maps_box.grid(row=2, column =2)
        self.maps_box.bind('<<ListboxSelect>>', self.preview)

        self.analysis_label = Label(self, text = 'Analysis path')
        self.analysis_label.grid(row=0, column =2)

        Button(self, text = 'Get atomic percentages', command = self.quantifications).grid(row=0,column=1)


    def quantifications(self) -> pd.DataFrame:
        result = []
        for name, analysis in self.quant_tables.items():
            tmp = pd.read_csv(analysis)
            col1 = tmp['Element symbol'].tolist()
            col2 = tmp['Atomic concentration percentage'].tolist()
            df = pd.DataFrame(columns=col1, data = [col2], index=[name])
            result.append(df)
        result = pd.concat(result)
        result.to_excel(f'{os.path.join(project_path, 'Quantification_summary.xlsx')}')


    def project_selection(self) -> dict:
        '''Folder dialog to select the Phenom project folder.
        Returns a dictionary containing all analyses and SEM photos'''
        global project_path
        self.photos_box.delete(0, END)
        self.maps_folders.delete(0,END)
        self.maps_box.delete(0, END)

        project_path = filedialog.askdirectory()
        save_location.configure(text=project_path)

        self.quant_tables = {}
        self.photos = { }
        self.maps = { }
        for root, dirs, files in os.walk(project_path):
            basename = os.path.basename(root)
            if '_map_' in basename and 'Export' in root:
                map_files = [file for file in files if 'pixel' in file]
                self.maps[basename] = EDS(path = root, maps = map_files)

            for file in files:
                if ('Export' not in root) and ('.tiff' in file):
                    self.photos[file] = SEM(path = root, filename = file)
                elif (basename == 'Export') and ('.tiff' in file):
                    self.photos['E_' + file] = SEM(path = root, filename = file)
                elif 'quantification.csv' in file:
                    self.quant_tables[basename] = os.path.join(root,file)
            
        
        for photo in self.photos.keys():
            self.photos_box.insert(END,photo)
        for EDS_analysis in self.maps.keys():
            self.maps_folders.insert(END,EDS_analysis)

    def show_maps(self, event = None):
               
        folder = self.maps_folders.get(self.maps_folders.curselection())
        self.analysis_label.configure(text = folder)
        if folder == None:
            pass
        self.maps_box.delete(0,END)
        
        self.tmp = self.maps[folder].dict
        for f in self.maps[folder].maps:
            self.maps_box.insert(0,f)
        

    
    def preview(self, event):
        global selected
        global preview_image
        global border

        sem_settings, map_settings, border = self.test()

        if event.widget == self.maps_box:
            selected = self.maps_box.get(self.maps_box.curselection())
            self.element_name = selected.split(' ')[0]
            selected = self.tmp[selected]
            selected = self.modify_map(image = selected, settings = map_settings)
            
            fill = (0,0,0)
        elif event.widget == self.photos_box:
            selected = self.photos_box.get(self.photos_box.curselection())
            selected = self.photos[selected].image
            selected = self.modify_SEM(image = selected, settings = sem_settings)
            fill = (0)


        tmp_border = int(float(border)/100*selected.size[0])
        preview_image = selected
        preview_image = ImageOps.expand(preview_image, border = tmp_border, fill = fill)
        preview_image_mini = ImageTk.PhotoImage(preview_image.resize((200,200)))
        self.preview_im.configure(image = preview_image_mini)
        self.preview_im.image = preview_image_mini
        
    
    def modify_map(self, image, settings):
        im = PIL.Image.open(image)
        im = im.crop((0,0,im.size[0],im.size[0]))
        if cut_var.get() == 1:
            position_dict = {'ld': ((0,im.size[0]), 'lb' ),
                            'rd': ((im.size[0], im.size[0]), 'rb'),
                            'lu':((0,0), 'lt'),
                            'ru':((im.size[0],0), 'rt') 
                            }

            mode, font, font_size = settings.values()
            font_size = int(font_size)/100 * im.size[0]
            self.font = ImageFont.truetype(font = font, size= font_size)

            position, anchor = position_dict[mode]
        
            if self.element_name == 'Aluminium':
                self.element_name = 'Aluminum'
            name = str(elements.name((self.element_name.lower())))

            draw = ImageDraw.ImageDraw(im)
            draw.text(position,text=name,font=self.font, anchor=anchor)
        
        return im
    
    def modify_SEM(self, image, settings):
        
        tmp = PIL.Image.open(image)
        im = tmp.crop((0,0,tmp.size[0],tmp.size[0]))
        if cut_var_SEM.get() == 1:
        
            mode, color, font, font_size, padding, scale_height = settings.values()
            font_size = int(font_size)/100 * im.size[0]
            self.font = ImageFont.truetype(font, size= font_size)   


            scalenumber, line_width = self.get_scale(tmp)
            
            scale_and_number = magnification_scale(scalenumber, 
                                                    line_width, 
                                                    font =self.font, 
                                                    font_size = font_size, 
                                                    imsize = im.size, 
                                                    mode = mode, 
                                                    scale_height = scale_height,
                                                    image = im,
                                                    padding = padding,
                                                    color = color)
            
        return im


    def get_scale(self, image):

        im = image
        pasek = im.crop((0,im.size[0],im.size[0]/2,im.size[1]))
        skala = pasek.crop((0,0,im.size[0]/3,pasek.size[1]))
        scale_number = pytesseract.image_to_string(skala,config=custom_config).strip()
        
        if ('u' in scale_number) or ('p' in scale_number):
            scale_number = scale_number.replace('u','\u03BC')
            scale_number = scale_number.replace('p','\u03BC')
        self.scale_number = scale_number
        pixels = list(skala.getdata())
        pasek_pixels = 0
        for i in range(skala.size[1]):
            row = pixels[i*skala.size[0]:(i+1)*skala.size[0]]
            tmp = row.count(185)
            if pasek_pixels < tmp:
                pasek_pixels = tmp
        
        return scale_number, pasek_pixels



class magnification_scale():

    def __init__(self, number, scale, font, imsize, font_size, mode, scale_height, image, padding, color):
        self.number = number
        self.scale = scale
        self.font = font
        self.im_x, self.im_y = imsize
        self.padx = float(padding[0])
        self.pady = float(padding[1])
        self.font_size = font_size
        self.mode = mode
        self.image = image
        self.scale_height = int(float(scale_height)/100*self.image.size[0])
        self.color = color
        self.get_position()

    def get_position(self):
        tmp = ImageDraw.ImageDraw(self.image)
        text_width = tmp.textlength(self.number, self.font)
        if text_width > self.scale:
            offset = text_width/2
        else: 
            offset = self.scale/2
        self.x = (1 - self.padx) *self.im_x - offset
        self.y = (1 - self.pady) *self.im_y - self.font_size/2
        descent = self.font.getmetrics()[1]

        if 'l' in self.mode:
            self.x = self.im_x - self.x
        if 'u' in self.mode:
            ascent = self.font.font.getsize(self.number)[1][1]
            self.y = self.im_y - self.y - ascent
        tmp.text((self.x, self.y), text = self.number, font = self.font, anchor = 'mm', fill = self.color)
        tmp.line([(self.x - 0.5 * self.scale, self.y + self.font_size/2 + descent + self.scale_height), 
                  (self.x + 0.5 * self.scale, self.y + self.font_size/2 + descent + self.scale_height)],
                    width = self.scale_height, fill = self.color)
        

    '''
    THESE FUNCTIONS ARE WORK IN PROGESS. WILL DO THEM EVENTUALLY. FOR NOW STICK TO SIMPLER POSITIONING FUNCTION
    def get_position(self):
        self.vertical = self.text_position.text_vertical
        self.vertical.bind('<ButtonRelease-1>', self.redraw)
        self.horizontal = self.text_position.text_horizontal
        self.horizontal.bind('<ButtonRelease-1>',self.redraw)
    
    def redraw(self, event):
        im = PIL.Image.open('test.tiff')
        self.draw = ImageDraw.ImageDraw(im)
        self.draw = self.draw.text((int(self.horizontal.get())/100*im.size[0],int(self.vertical.get())/100*im.size[0]), text = 'Naura', font = self.font, anchor = 'lt'  )
        im.show()
    '''

class SEM():
    def __init__(self, path, filename):
        self.path = path
        self.filename = filename
        self.image = os.path.join(path,filename)

class EDS():
    def __init__(self, path, maps):

        self.path = path
        self.maps = maps
        self.dict = {m: os.path.join(path,m) for m in maps}


class Preview(LabelFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(text = 'Preview')
        
        self.preview_image = Label(self, image = PhotoImage(height=1, width= 1), height = 250, width = 250)
        self.preview_image.pack()

        '''
        WORK IN PROGESS. THIS WILL BE BETTER THAN DEFAULT 4 POSITIONS ON IMAGE. FOR MORE INFO SEE redraw() FUNCTION IN OPTIONS CLASS
        self.text_horizontal = Scale(self, orient = 'horizontal', from_ = 0, to = 100, length = 150, resolution = 1)
        self.text_horizontal.pack()
        self.text_vertical = Scale(self, orient = 'horizontal', from_ = 0, to = 100, length = 150, resolution = 1)
        self.text_vertical.pack()
        '''

class Grid_Frame(LabelFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent)
        self.configure(text = 'Grid')
        self.the_grid = the_Grid(self)
        self.the_grid.place(rely=0.15, relx=0, relheight = 0.85, relwidth = 1)

        self.create_widgets()

    
    def create_widgets(self):
        global save_location
        self.grid_options = LabelFrame(self, text = 'Grid options')
        self.grid_options.place(relx=0, rely=0, relheight=0.15, relwidth = 1)



        Label(self.grid_options, text = 'Number of columns').grid(row=0,column=0)
        self.grid_columns = Entry(self.grid_options)
        self.grid_columns.grid(row=1,column=0)
        self.grid_columns.insert(0,3)
        Label(self.grid_options, text = 'Number of rows').grid(row=0,column=1)
        self.grid_rows = Entry(self.grid_options)
        self.grid_rows.grid(row=1,column=1, sticky = N+S+E+W)
        self.grid_rows.insert(0,3)

        Button(self.grid_options, text = 'Generate grid', command = self.generate_grid).grid(row=1,column=3)

        Label(self.grid_options, text = 'Photo size [px]').grid(row=0, column = 2)
        self.labelsize = Entry(self.grid_options)
        self.labelsize.grid(row = 1, column =2)
        self.labelsize.insert(0,1024)
        
        Label(self.grid_options, text = 'Current save loction:').grid(row=2, column = 0)
        save_location = Label(self.grid_options)
        save_location.grid(row=2, column=1, columnspan= 4)


        Button(self.grid_options, text = 'Save as', command = self.save_image).grid(row=1, column=4)


    def generate_grid(self):
        global labelsize
    
        height = self.the_grid.winfo_height()
        width = self.the_grid.winfo_width()

        cols = int(self.grid_columns.get())
        rows = int(self.grid_rows.get())
        labelsize = int(self.labelsize.get())


        size1 = width/cols
        size2 = height/rows
        if size1 > size2:
            size = size2
        else:
            size = size1

        for slave in self.the_grid.winfo_children():
            slave.destroy()
        for col in range(cols):
            for row in range(rows):
                
                #subtracting 5 from size is due to the fact that the last column was cropped
                Grid_label(self.the_grid, preview_size = size-5, image_size = labelsize).grid(row=row, column= col)
        
    def save_image(self):
        labelsize = int(self.labelsize.get())
        bord = int(float(border)/100*labelsize)
        slaves = {(slave.grid_info()['column'], slave.grid_info()['row']):slave.im for slave in self.the_grid.winfo_children() if slave.im != None}
        a = list(slaves.keys())
        x, y = max([b[0] for b in a]), max(([b[1] for b in a]))
        x_max, y_max = x+1, y+1
        
        #This is derived from the space images occupy with borders included
        #x_max * labelsize + (1+x) * bord

        self.final_image = PIL.Image.new('RGBA', (x_max * labelsize + (2 + x) * bord , 
                             y_max * labelsize + (2 + y) * bord ))
        
        for coords, image in slaves.items():
            
            tmp = image.resize((labelsize,labelsize))
            try:
                tmp = ImageOps.expand(tmp, bord, fill = (0,0,0))
            except:
                tmp = ImageOps.expand(tmp, bord, fill = 0)
            

            if coords[0] == 0:
                paste = 0
            else:
                paste = labelsize*coords[0]+ bord*coords[0]
            if coords[1] == 0:
                paste2 = 0
            else:
                paste2 = labelsize*coords[1] +bord*coords[1]
            self.final_image.paste(tmp, (paste, paste2))

        files = [("Tagged Image File Format; *.tiff","*.tiff"),
                 ("Portable Network Graphics; *.png","*.png"),
                ("Joint Photographic Experts Group; *.jpeg","*.jpeg")]
        f = filedialog.asksaveasfile(defaultextension= files, filetypes = files)
        print(f)
        try:
            self.final_image.save(f.name)
        except:
            print('Wrong extension')




class the_Grid(Frame):
    def __init__(self, parent):
        
        super().__init__(parent)
        pass
    

class Grid_label(Label):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent)
        self.preview_size = kwargs['preview_size']
        self.im = None
        self.master = parent
        self.configure(image = PhotoImage(height = 1, width = 1, name = 'blank'), height = self.preview_size, width = self.preview_size, relief = 'groove', borderwidth = 1)
        self.bind('<Button-1>', self.click, add = "+")
        
    def click(self, event):
        tmp = preview_image.resize((int(self.preview_size), int(self.preview_size)))
        tmp = ImageTk.PhotoImage(tmp)
        event.widget.configure(image=tmp)
        event.widget.image = tmp
        self.im = selected


class ImageOptions(LabelFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent)
        self.configure(text= 'Image options', pady = 25, padx = 25, relief = 'solid', borderwidth=2)

        Label(self, text = 'Border width [image %]').pack()
        self.border = ttk.Combobox(self ,value = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], width = 5)
        self.border.pack()
        self.border.set(1)

        self.SEM_options = SEMOptions(self)
        self.SEM_options.pack(expand=True, fill = 'both')

        self.MAP_options = MapOptions(self)
        self.MAP_options.pack(expand=True, fill ='both')

    def get_options(self):
        return self.SEM_options.dictionary_update(), self.MAP_options.dictionary_update(), self.border.get()

class SEMOptions(LabelFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent)
        self.configure(text = 'SEM photo settings')
        global cut_var_SEM
        

        cut_var_SEM = IntVar()
        cut_var_SEM.set(1)
        self.cut = Checkbutton(self, text = 'Modify SEM image', variable = cut_var_SEM, command = self.check_state)
        self.cut.pack()

        self.v = StringVar(self, "rd")
        values = {"Left upper" : ("lu", 1, 0), 
                "Right upper" : ("ru", 2 ,0),
                "Left down" : ("ld", 1, 1),
                "Right down" : ("rd", 2, 1)}
        
        # Loop is used to create multiple Radiobuttons 
        # rather than creating each button separately 
        self.x = LabelFrame(self, text = 'Scale placement')
        self.x.pack(padx=10, pady= 10)
        Label(self.x, text = 'Placement').grid(column=0, row=0)
        for (text, value) in values.items(): 
            self.Radio = Radiobutton(self.x, text = text, variable = self.v, 
                value = value[0]).grid(column = value[1], row = value[2])
        self.padx = Scale(self.x, orient = 'horizontal', from_=0.05, to=0.25, length = 150, resolution = 0.025)
        self.padx.grid(column=1, row= 3, columnspan=2)
        Label(self.x, text = 'padx').grid(column=0,row=3)
        Label(self.x, text = 'pady').grid(column=0,row=4)
        self.pady = Scale(self.x, orient = 'horizontal', from_=0.05, to=0.25, length = 150, resolution = 0.025)
        self.pady.grid(column=1, row= 4, columnspan=2)

        self.y = LabelFrame(self, text = 'Scale and font color')
        self.y.pack(padx=10, pady=10)
        
        Label(self.y, text = 'Text color (grayscale)').grid(row=0, column =0)
        self.scale = Scale(self.y, orient = 'horizontal', from_=0, to=255, length = 150, resolution = 5)
        self.scale.grid(row=1, column=0, padx= 10, pady = 10)
        self.scale.bind("<ButtonRelease-1>", self.update_scale)
        Label(self.y, text = 'Preview').grid(row=0,column=1)
        self.Eo = Label(self.y,  width = 3, height = 1,  background = 'Black', borderwidth = 1, relief = 'solid')
        self.Eo.grid(row=1, column = 1)

        Label(self.y, text = 'Font').grid(row = 2, column =0)
        self.fonts = ttk.Combobox(self.y, values = list(font_families.keys()), width = 20 )
        self.fonts.set('Century Gothic')
        self.fonts.grid(row=3, column= 0)
        self.fonts.bind('<<ComboboxSelected>>', self.get_font_styles)


        Label(self.y, text = 'Style').grid(row =2, column =1)
        self.style = ttk.Combobox(self.y, width = 10)
        self.style.grid(row=3, column =1)
        self.get_font_styles()

        Label(self.y, text = 'Size (%)').grid(row= 2, column = 2)
        self.font_size = ttk.Combobox(self.y, value = [1, 2, 3, 4, 5, 10], width = 5, text = 'elo')
        self.font_size.set(10)
        self.font_size.grid(row = 3, column = 2)

        Label(self.y, text = 'Scale height').grid(row=0, column=2)
        self.scale_height = ttk.Combobox(self.y, value = [1, 2, 3, 4, 5], width = 5)
        self.scale_height.set(1)
        self.scale_height.grid(row=1, column =2 )

        self.dictionary = [self.v.get(), self.scale.get(), self.fonts.get(), self.font_size.get(), self.scale_height.get()]
        
    def check_state(self, event = None):
        slaves = self.x.winfo_children() + self.y.winfo_children()
        for slave in slaves:
            if cut_var_SEM.get() == 0:
                slave.configure(state = 'disabled')
            else:
                slave.configure(state= 'normal')

    def get_font_styles(self, event = None):
        self.style.delete(0,END)
        avaiable_styles = list(font_families[self.fonts.get()])
        self.style['values'] = avaiable_styles
        self.style.set(avaiable_styles[0])     
        
    def update_scale(self, event = None):
        self.clr = int(self.scale.get())
        self.clr = '#%02x%02x%02x' % (self.clr, self.clr, self.clr)
        self.Eo.configure(background = self.clr)

    def dictionary_update(self):
        self.dictionary = {'Position':self.v.get(),
                           'Color': self.scale.get(),
                            'Font': font_families[self.fonts.get()][self.style.get()],
                             'Font_size': self.font_size.get(),
                             'Padding': (self.padx.get(), self.pady.get()),
                             'Scale height': self.scale_height.get()}
        return self.dictionary

class MapOptions(LabelFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent)
        self.configure(text = 'Map photo settings')
        global cut_var
        cut_var = IntVar()
        cut_var.set(1)
        self.cut = Checkbutton(self, text = 'Modify map image', variable = cut_var, command = self.check_state)
        self.cut.pack()

        self.v = StringVar(self, "rd")
        values = {"Left upper" : ("lu", 0, 0), 
                "Right upper" : ("ru", 1 ,0),
                "Left down" : ("ld", 0, 1),
                "Right down" : ("rd", 1, 1)}
        
        # Loop is used to create multiple Radiobuttons 
        # rather than creating each button separately 
        self.x = LabelFrame(self, text = 'Element name placement')
        self.x.pack(padx=10, pady= 10)
        for (text, value) in values.items(): 
            self.Radio = Radiobutton(self.x, text = text, variable = self.v, 
                value = value[0]).grid(column = value[1], row = value[2], pady = 5)

        self.y = LabelFrame(self, text = 'Font')
        self.y.pack(padx=10, pady=10)

        Label(self.y, text = 'Font').grid(row = 1, column =0)
        self.fonts = ttk.Combobox(self.y, values = list(font_families.keys()), width = 20 )
        self.fonts.set('Century Gothic')
        self.fonts.grid(row=2, column= 0)
        self.fonts.bind('<<ComboboxSelected>>', self.get_font_styles)


        Label(self.y, text = 'Style').grid(row =1, column =1)
        self.style = ttk.Combobox(self.y, widt=10)
        self.style.grid(row=2, column =1)
        self.get_font_styles()


        Label(self.y, text = 'Size (%)').grid(row= 1, column = 2)
        self.font_size_map = ttk.Combobox(self.y, value = [10, 20, 25, 30, 35], width = 5)
        self.font_size_map.set(30)
        self.font_size_map.grid(row = 2, column = 2)
        
    def check_state(self, event = None):
        slaves = self.x.winfo_children() + self.y.winfo_children()
        for slave in slaves:
            if cut_var.get() == 0:
                slave.configure(state = 'disabled')
            else:
                slave.configure(state= 'normal')
    
    def get_font_styles(self, event = None):
        self.style.delete(0,END)
        avaiable_styles = list(font_families[self.fonts.get()])
        self.style['values'] = avaiable_styles
        self.style.set(avaiable_styles[0])       
    
    def dictionary_update(self):
        self.dictionary = {'Position':self.v.get(),
                           'Font': font_families[self.fonts.get()][self.style.get()],
                            'Font_size': self.font_size_map.get()}
        return self.dictionary

    

App('elo',(1300,1000))