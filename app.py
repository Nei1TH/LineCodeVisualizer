import tkinter as tk
from tkinter import ttk, messagebox

class LineCodingVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Line Coding Visualizer - Engineering Edition")
        self.root.geometry("1100x850")
        
        # --- Engineering Parameters ---
        self.bit_width = 60   # Pixels per bit duration
        self.h_scale = 25     # Vertical scale factor (Voltage to Pixels)
        self.max_bits = 16    # Input limit (Updated to 16 as requested)
        self.y_gap = 120      # Gap between different encoding plots (Increased to prevent overlap)
        self.start_y_offset = 60 # Initial Y offset for the first plot
        
        # UI Construction
        self.setup_ui()
        
    def setup_ui(self):
        # --- 1. Top Control Panel ---
        control_panel = ttk.Frame(self.root, padding="10")
        control_panel.pack(fill=tk.X)
        
        # Input Section
        input_frame = ttk.LabelFrame(control_panel, text="Input Signal", padding="5")
        input_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        ttk.Label(input_frame, text=f"Binary (Max {self.max_bits}):").pack(side=tk.LEFT)
        self.entry_bits = ttk.Entry(input_frame, width=20, font=("Consolas", 10))
        self.entry_bits.pack(side=tk.LEFT, padx=5)
        # Default value for quick testing
        self.entry_bits.insert(0, "01001100011")
        
        # Initial State Section (The Logic Fix)
        state_frame = ttk.LabelFrame(control_panel, text="Initial State Assumption", padding="5")
        state_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        self.init_level = tk.IntVar(value=1) # Default High (+1)
        ttk.Radiobutton(state_frame, text="+1 (High)", variable=self.init_level, value=1).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(state_frame, text="-1 (Low)", variable=self.init_level, value=-1).pack(side=tk.LEFT, padx=5)
        
        # Action Button
        btn_plot = ttk.Button(control_panel, text="Plot Signals", command=self.process_and_plot)
        btn_plot.pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        # --- 2. Encoding Selection Panel ---
        selection_frame = ttk.LabelFrame(self.root, text="Select Encoding Schemes", padding="5")
        selection_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.codes = {
            "Unipolar NRZ": tk.BooleanVar(value=True),
            "Polar NRZ-L": tk.BooleanVar(value=True),
            "Polar NRZ-I": tk.BooleanVar(value=True), # State dependent
            "Polar RZ": tk.BooleanVar(value=False),
            "AMI": tk.BooleanVar(value=True),         # State dependent
            "Manchester": tk.BooleanVar(value=True),
            "Diff. Manchester": tk.BooleanVar(value=True), # State dependent
            "MLT-3": tk.BooleanVar(value=True),       # State dependent
            "2B1Q": tk.BooleanVar(value=False)
        }
        
        # Grid layout for checkboxes (max 5 columns)
        row, col = 0, 0
        for name, var in self.codes.items():
            cb = ttk.Checkbutton(selection_frame, text=name, variable=var)
            cb.grid(row=row, column=col, sticky="w", padx=10, pady=2)
            col += 1
            if col > 4:
                col = 0
                row += 1

        # --- 3. Canvas Area (Scrollable) ---
        self.canvas_frame = ttk.Frame(self.root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="white")
        
        # Scrollbar logic
        v_scroll = ttk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=v_scroll.set)
        
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind scroll event
        self.canvas_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))


    def get_signal_data(self, bits, encoding, init_level):
        """
        Core Logic Engine.
        Converts bits to voltage levels based on encoding rules and initial state.
        Returns: List of levels (2 samples per bit duration).
        """
        data = []
        
        if encoding == "Unipolar NRZ":
            # 1=+1, 0=0 (Independent of previous)
            for b in bits:
                val = 1 if b == '1' else 0
                data.extend([val, val])

        elif encoding == "Polar NRZ-L":
            # 1=-1, 0=+1 (Standard convention, independent)
            for b in bits:
                val = -1 if b == '1' else 1
                data.extend([val, val])

        elif encoding == "Polar NRZ-I":
            # Transition on 1, Hold on 0 (Dependent)
            current = init_level
            for b in bits:
                if b == '1':
                    current *= -1
                data.extend([current, current])

        elif encoding == "Polar RZ":
            # 1: +1->0, 0: -1->0 (Independent)
            for b in bits:
                if b == '1':
                    data.extend([1, 0])
                else:
                    data.extend([-1, 0])

        elif encoding == "AMI":
            # 0=0, 1=Alternating +/- (Dependent on last 1)
            # Logic: If init_level is +1, we assume the "virtual previous 1" was -1, so next is +1.
            # If init_level is -1, we assume previous was +1.
            # Effectively: first '1' becomes init_level.
            
            # To achieve "First 1 is init_level":
            # last_one needs to be the OPPOSITE of init_level
            last_one = -1 * init_level 
            
            for b in bits:
                if b == '0':
                    data.extend([0, 0])
                else:
                    last_one *= -1
                    data.extend([last_one, last_one])

        elif encoding == "Manchester":
            # 1 = Low->High, 0 = High->Low (Independent)
            for b in bits:
                if b == '1':
                    data.extend([-1, 1])
                else:
                    data.extend([1, -1])

        elif encoding == "Diff. Manchester":
            # Transition at mid-bit always.
            # 0: Transition at start. 1: No transition at start.
            current = init_level
            
            # Important: Diff Manchester logic implies we start from a state.
            # If start bit is 0, we flip immediately. If 1, we hold then flip mid.
            
            for b in bits:
                if b == '0':
                    current *= -1 # Transition at start
                
                first_half = current
                current *= -1 # Mid-bit transition ALWAYS
                second_half = current
                
                data.extend([first_half, second_half])

        elif encoding == "MLT-3":
            # +1, 0, -1, 0 sequence. Change on 1, Hold on 0.
            curr_level = 0
            # To ensure the first '1' goes towards our init_level (sort of),
            # or simply assume init_level is the "last non-zero" direction reference.
            # Let's align it: if user selects +1, first transition goes positive.
            last_non_zero = -1 * init_level 
            
            for b in bits:
                if b == '1':
                    if curr_level != 0:
                        curr_level = 0
                    else:
                        # Move to next non-zero
                        curr_level = -1 * last_non_zero
                        last_non_zero = curr_level
                data.extend([curr_level, curr_level])

        elif encoding == "2B1Q":
            # 00=+1, 01=+3, 10=-1, 11=-3 (Independent)
            mapping = {'00': 1, '01': 3, '10': -1, '11': -3}
            # Pad if odd length
            bits_proc = bits if len(bits) % 2 == 0 else bits + '0'
            
            for i in range(0, len(bits_proc), 2):
                pair = bits_proc[i:i+2]
                val = mapping.get(pair, 0)
                # 2B1Q symbol duration is 2 bit slots.
                # Visualizer uses 2 samples per bit -> 4 samples per symbol
                data.extend([val, val, val, val]) 

        return data

    def process_and_plot(self):
        # 1. Input Validation
        bits_raw = self.entry_bits.get().strip()
        
        if not bits_raw:
            return
        
        # Filter non-binary chars
        bits = "".join([c for c in bits_raw if c in '01'])
        
        if len(bits) != len(bits_raw):
             messagebox.showwarning("Data Cleaned", "Removed non-binary characters.")
        
        if len(bits) > self.max_bits:
            messagebox.showwarning("Truncated", f"Input truncated to {self.max_bits} bits.")
            bits = bits[:self.max_bits]
            
        # 2. Setup Canvas
        self.canvas.delete("all")
        active_codes = [name for name, var in self.codes.items() if var.get()]
        
        # Get Initial State from UI
        init_level = self.init_level.get()
        
        # 3. Draw Global Time Grid
        total_height = self.start_y_offset + len(active_codes) * self.y_gap + 50
        total_width = 80 + len(bits) * self.bit_width + 50
        # Expand canvas scroll region
        self.canvas.configure(scrollregion=(0, 0, total_width, total_height)) 
        
        # Draw vertical grid lines
        for i in range(len(bits) + 1):
            x = 80 + i * self.bit_width # 80 is left margin
            self.canvas.create_line(x, 0, x, total_height, fill="#e0e0e0", dash=(4, 4))
            # Bit labels at top
            if i < len(bits):
                self.canvas.create_text(x + self.bit_width/2, 25, text=bits[i], 
                                      font=("Consolas", 12, "bold"), fill="#333")

        # 4. Plot Each Encoding
        current_baseline_y = self.start_y_offset + 30 # +30 to push down from bit labels
        
        for name in active_codes:
            # A. Draw Title (Moved up to avoid overlap)
            self.canvas.create_text(10, current_baseline_y - 30, text=name, anchor="w", 
                                  font=("Helvetica", 10, "bold"), fill="blue")
            
            # B. Draw Zero Line (Baseline)
            end_x = 80 + len(bits) * self.bit_width
            self.canvas.create_line(80, current_baseline_y, end_x, current_baseline_y, fill="#999", width=1)
            self.canvas.create_text(70, current_baseline_y, text="0", fill="#999", font=("Arial", 8))
            
            # C. Get Data
            levels = self.get_signal_data(bits, name, init_level)
            
            # D. Draw Waveform
            step_w = self.bit_width / 2 # Sample width (half-bit)
            
            # Handle 2B1Q visual scaling (it has fewer symbols than bits)
            if name == "2B1Q":
                # Data length matches (padded) bits * 2
                pass 
                
            prev_x = 80
            # Calculate initial Y based on first level
            prev_y = current_baseline_y - (levels[0] * self.h_scale)
            
            # Optional: Draw faint line from 'previous state' if you really want to show continuity
            # self.canvas.create_line(70, prev_y, 80, prev_y, fill="gray", dash=(2,2))

            for i, lvl in enumerate(levels):
                x = 80 + (i+1) * step_w
                y = current_baseline_y - (lvl * self.h_scale)
                
                # Critical Engineering Drawing: Vertical Rise/Fall
                if i > 0:
                    last_lvl = levels[i-1]
                    last_y = current_baseline_y - (last_lvl * self.h_scale)
                    
                    # If voltage changed, draw vertical line at the boundary
                    if last_y != y:
                        self.canvas.create_line(80 + i * step_w, last_y, 80 + i * step_w, y, 
                                              fill="#d32f2f", width=2)
                
                # Draw Horizontal Level
                self.canvas.create_line(80 + i * step_w, y, x, y, fill="#d32f2f", width=2)
                
            # Move to next slot
            current_baseline_y += self.y_gap

if __name__ == "__main__":
    root = tk.Tk()
    app = LineCodingVisualizer(root)
    root.mainloop()