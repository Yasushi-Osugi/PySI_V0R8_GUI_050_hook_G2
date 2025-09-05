#load_data_files_NEW.py

def load_data_files(self):
    directory = filedialog.askdirectory(title="Select Data Directory")
    if not directory:
        return

    try:
        self.lot_size = int(self.lot_size_entry.get())
        self.plan_year_st = int(self.plan_year_entry.get())
        self.plan_range = int(self.plan_range_entry.get())
    except ValueError:
        print("Invalid input. Using default values.")

    self.directory = directory
    self.load_directory = directory
    self.outbound_data = []
    self.inbound_data = []

    # Load tree structures
    self.load_tree_structures(directory)

    # Load cost tables
    self.load_cost_tables(directory)

    # Convert monthly demand to weekly
    df_weekly = self.convert_monthly_to_weekly(directory)

    # Initialize PSI spaces
    self.initialize_psi_spaces(df_weekly)

    # Perform allocation using P_month_data
    self.perform_allocation_from_template(directory)

    # Finalize allocation and redraw
    self.finalize_allocation_and_render()

    # Update evaluation and view
    self.update_evaluation_results()
    self.view_nx_matlib4opt()
    self.root.after(1000, self.show_psi("outbound", "supply"))

    # GUI setup
    self.initialize_parameters()
    self.supply_planning_button.config(state="normal")
    self.eval_buffer_stock_button.config(state="normal")

    print("Data files loaded and buttons enabled.")


