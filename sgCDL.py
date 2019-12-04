"Set the OS ENV SGCDL_WORKING_SPACE to change it's setting"

def getCDLFromShotgun():
    print " "
    import nuke
    import os
    import sys

    def logSmall(msg):
        print "-  "+msg

    def log(msg):
        print "#############################"
        print msg
        print "#############################"


    ###############################
    log("sgCDL")
    ###############################
    n = nuke.thisNode()
    n["lbl_context"].setValue("")    
    app_version = os.path.basename(os.path.dirname(__file__))
    n["lbl_version"].setValue(app_version)

    
    ###############################
    logSmall("Connecting to Shotgun")
    ###############################
    mode = "CMD"
    try:
        import sgtk
        # get the engine we are currently running in
        current_engine = sgtk.platform.current_engine()
        # get hold of the shotgun api instance used by the engine, (or we could have created a new one)
        sg = current_engine.shotgun
        logSmall("Connected to Shotgun via current SGTK engine...\n")
        mode = "GUI"
    except:
        try:
            sys.path.append(os.environ["SHOTGUN_API3"])
            import shotgun_api3
            sg = shotgun_api3.Shotgun(os.environ["SHOTGUN_API_SERVER_PATH"], os.environ["SHOTGUN_API_SCRIPT_NAME"], os.environ["SHOTGUN_API_SCRIPT_KEY"])
            logSmall("Connected to Shotgun via api...\n")
        except Exception as e:
            logSmall(str(e))
            if nuke.GUI:
                nuke.message(str(e))
            return


    def findParentNode(current_node, parent_class):
        parent_node = current_node.input(0)
        if parent_node.Class() == parent_class:
            print "Found Parent node: "+parent_node["name"].getValue()
            #return parent_node["name"].getValue()
            os.environ["PARENT_NODE"] = parent_node["name"].getValue()
            return
        else:
            print "Trying to Find Parent Node: "+parent_node["name"].getValue()
            findParentNode(parent_node, parent_class)

    
    def getCDLFromShotgun(sg_shot):
        asc_sat = sg_shot["sg_cdl_asc_sat"]
        asc_sop = sg_shot["sg_cdl_asc_sop"]

        "If no values, set default"
        if  asc_sat == None:
            asc_sat = str(1)
            logSmall("Could not find SAT value so setting to default")
        if asc_sop == None:
            asc_sop = "(1 1 1)(0 0 0)(1 1 1)"
            logSmall("Could not find SOP value so setting to default")

        setCDL(asc_sat, asc_sop)

            
    def setCDL(sat, sop):                
        ####################################################
        logSmall("Processing CDL values!...")
        ####################################################
        "Set saturation Knob"
        n["saturation"].setValue(float(sat))

        "Set SOP knobs"
        sop = sop.split(")(")

        "Slope"
        slope = sop[0].replace("(", "")
        slope = slope.replace(")", "")
        slope = slope.split(" ")
        vals = [float(slope[0]), float(slope[1]), float(slope[2])]
        n["slope"].setValue(vals)

        "Offset"
        offset = sop[1].replace("(", "")
        offset = offset.replace(")", "")
        offset = offset.split(" ")
        vals = [float(offset[0]), float(offset[1]), float(offset[2])]
        n["offset"].setValue(vals)

        "Power"
        power = sop[2].replace("(", "")
        power = power.replace(")", "")
        power = power.split(" ")
        vals = [float(power[0]), float(power[1]), float(power[2])]
        n["power"].setValue(vals)

        "Working Space"
        try:
            n["working_space"].setValue(os.environ["SGCDL_WORKING_SPACE"])
        except:
            pass

        #"Update Context Label"
        #n["lbl_context"].setValue(sg_shot["code"])
        
        return
    
    

    ##################################################################################
    "COMMANDLINE MODE"
    ##################################################################################
    if not nuke.GUI:
        logSmall("Mode: CMD")

        "Find Parent Read Node"
        findParentNode(n, "Read")
        read = nuke.toNode(os.environ["PARENT_NODE"])

        "Find Shot based on version data"
        filters = [ ["sg_path_to_frames", "contains", read["file"].getValue()] ]
        fields = ["entity"]
        sg_version = sg.find_one("Version", filters, fields)
        
        if sg_version == None:
            filters = [ ["sg_path_to_frames", "contains", read["file"].getValue().replace("/", "\\")] ]
            fields = ["entity"]
            sg_version = sg.find_one("Version", filters, fields)
        
        print sg_version

        "Find Shot"
        filters = [ ["id", "is", sg_version["entity"].get("id")] ]
        fields = ["code", "sg_cdl_asc_sat", "sg_cdl_asc_sop"]
        sg_shot = sg.find_one("Shot", filters, fields)

        getCDLFromShotgun(sg_shot)




    ##################################################################################
    "GUI MODE"
    ##################################################################################
    if nuke.GUI:
        logSmall("Mode: GUI")

        ####################################################
        "NODE IS CONNECTED TO A PIPE"
        ####################################################
        "If connected, find the parent Read node and Load CDL values if possible"
        if n.input(0) != None:
            #################################################
            logSmall("Finding Context of Parent Read Node")
            #################################################
            findParentNode(n, "Read")
            read = nuke.toNode(os.environ["PARENT_NODE"])

            tk = sgtk.sgtk_from_path(read["file"].getValue())
            ctx = tk.context_from_path(read["file"].getValue())
            
            filters = [ ["id", "is", ctx.entity["id"]] ]
            fields = ["code", "sg_cdl_asc_sat", "sg_cdl_asc_sop"]
            sg_shot = sg.find_one("Shot", filters, fields)
            #print sg_shot

            getCDLFromShotgun(sg_shot)
            



        ####################################################
        "NODE IS NOT CONNECTED TO A PIPE"
        ####################################################
        "If not connected, allow to select a shot to load the CDl from"
        if n.input(0) == None:
            try:
                "Get a List of Shotgun shots"
                tk = sgtk.sgtk_from_path(nuke.root()["name"].getValue())
                ctx = tk.context_from_path(nuke.root()["name"].getValue())

                filters = [ ["project", "is", ctx.project], ["sg_cdl_asc_sat", "is_not", None], ["sg_cdl_asc_sop", "is_not", None] ]
                fields = ["code"]
                sg_shots = sg.find("Shot", filters, fields)
                if sg_shots == []:
                    msg = "No Shots found that have CDL data"
                    try:
                        nuke.message(msg)
                    except:
                        logSmall(msg)
                    shot_choice = ""
                else:
                        
                    shots = []
                    for shot in sg_shots:
                        shots.append(shot["code"])
                    shots.sort()

                    ################################################
                    "Selection Panel"
                    ################################################
                    p = nuke.Panel("Select Shot to Load CDL from...")
                    lbl_choice = "Load CDL from Shot:"
                    p.addEnumerationPulldown(lbl_choice, " ".join(shots))
                    ret = p.show()

                    "Return if cancel is pressed"
                    if ret == 0:
                        return

                    shot_choice = p.value(lbl_choice)
                filters = [ ["code", "is", shot_choice] ]
                fields = ["code", "sg_cdl_asc_sat", "sg_cdl_asc_sop"]
                sg_shot = sg.find_one("Shot", filters, fields)
                #print sg_shot

                getCDLFromShotgun(sg_shot)

            except Exception as e:
                logSmall(str(e))
                if nuke.GUI:
                    nuke.message(str(e))
                return
        

