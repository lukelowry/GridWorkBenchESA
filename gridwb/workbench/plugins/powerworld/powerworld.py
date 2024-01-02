
from ...grid.builders import GridType
from ...interfaces.model import IModelIO
from ....saw import SAW

from os import path
from pandas import DataFrame, concat, to_numeric

# PW Fields to Retrieve
fieldMap: dict[GridType, list[str]] = {
    GridType.Region: [
        "SAName"
    ],
    GridType.Area: [
        "AreaNum"         , 
        "SAName"          , 
        "AreaName"        , 
    ],
    GridType.Sub: [
        "SubNum"          ,             
        "AreaNum"         ,             
        "SubName"         ,             
        "Latitude"        ,         
        "Longitude"       ,         
    ],
    GridType.Bus: [
        "BusNum"          ,          
        "SubNum"          ,             
        "BusName"         ,             
        "BusNomVolt"      ,         
        "BusPUVolt"       ,         
        "BusAngle"        ,         
        "BusStatus"       ,      
        "ZoneNum"         ,             
    ],
    GridType.Gen: [
        "GenID"           ,             
        "BusNum"          ,             
        "GenStatus"       ,         
        "GenMW"           ,         
        "GenMVR"          ,         
        "GenMWSetPoint"   ,         
        "GenMvrSetPoint"  ,         
        "GenMWMax"        ,             
        "GenMWMin"        ,             
        "GenMVRMax"       ,             
        "GenMVRMin"       ,             
        "GenRegNum"       ,             
        "GenVoltSet"      ,             
        "GenAGCAble"      ,       
        "GenAVRAble"      ,        
        "GenMWRampLimit"  ,             
        "CustomFloat"     ,             
        "CustomFloat:1"   ,             
        "CustomFloat:2"   ,             
        "GenFuelType"     ,             
        "GenFuelCost"     ,             
        "GenMVABase"      ,         
    ],
    GridType.Load: [
        "LoadID"      ,                
        "BusNum"      ,                
        "LoadStatus"  ,           
        "LoadMW"      ,            
        "LoadMVR"     ,            
        "LoadSMW"     ,            
        "LoadSMVR"    ,            
        "GenBidMWHR"  ,            
    ],
    GridType.Shunt: [
        "ShuntID"         ,              
        "BusNum"          ,             
        "SSStatus"        ,         
        "SSNMVR"          ,          
        "SSAMVR"          ,          
        "CustomInteger"   ,              
    ],
    GridType.Line: [
        "LineCircuit"     ,                
        "BusNum"          ,                
        "BusNum:1"        ,                
        "LineStatus"      ,          
        "LineR"           ,            
        "LineX"           ,            
        "LineC"           ,            
        "LineG"           ,            
        "LineAMVA"        ,            
        "LineAMVA:1"      ,            
        "LineAMVA:2"      ,            
        "LineMW"          ,            
        "LineMVR"         ,            
        "LineMW:1"        ,            
        "LineMVR:1"       ,             
        "GICLineDistance" ,          
        "CustomInteger",           
    ],
    # TODO Find way to Standardize
    GridType.TSContingency: [
        "TSCTGName",        
        "TSTimeInSeconds",         
        "TimeStep",          
        "Category",           
        "CTGSkip",       
        "CTGViol",         
        "TSTotalLoadMWTripped",      
        "TSTotalLoadMWIslanded"         
    ],
    GridType.TSContingencyAction: [
        "TSCTGName"        ,          
        "TSEventString"    ,           
        "WhoAmI"           ,           
        "TSTimeInSeconds"  ,         
    ],
    GridType.Contingency: [
        "CTGLabel",           
        "CTGSkip",           
        "CTGViol"         
    ],
    GridType.ContingencyAction: [
        "CTGLabel" ,           
        "Action"   ,           
        "Object"   ,            
        "WhoAmI"          
    ]
    
}

# Power World Read/Write
class PowerWorldIO(IModelIO):

    # Map GWB Types to PW Obj Type
    otypemap: dict[GridType, str] = {
        GridType.Region : 'superarea',
        GridType.Area   : 'area',
        GridType.Sub    :'substation',
        GridType.Bus    :'bus',
        GridType.Gen    :'gen',
        GridType.Load   :'load',
        GridType.Shunt  :'shunt',
        GridType.Line   :'branch',
        GridType.XFMR   :'xfmr',
        GridType.Contingency         : 'contingency',
        GridType.ContingencyAction   : 'contingencyelement',
        GridType.TSContingency       : 'tscontingency',
        GridType.TSContingencyAction : 'tscontingencyelement',
    }

    def open(self):
        
        # Validate Path Name
        if not path.isabs(self.fname):
            self.fname = path.abspath(self.fname)

        # ESA Object & Transient Sim
        self.esa = SAW(self.fname, CreateIfNotFound=True, early_bind=True)

    def download(self):

        # Create Empty DF
        data = super().Template.copy()

        # For Each GridObject
        for otype in fieldMap:

            # TODO might not need field list aabove with this
            keys = self.esa.get_key_field_list(self.otypemap[otype])

            # Get & Format Data for Objs of Specific Type
            df = self.esa.GetParametersMultipleElement(
                self.otypemap[otype],
                fieldMap[otype]
            ).stack().reset_index().rename(columns={
                'level_0' : 'ObjectID',
                'level_1' : 'Field',
                0         : 'Value'
            })

            # Added/Modify Fields
            if len(data) > 0:
                df['ObjectID'] += data['ObjectID'].max() + 1
            df['ObjectType'] = otype
            df['IsKey'] = df['Field'].isin(keys)

            # Merge With Previous Request
            data = concat([data,df], ignore_index=True)

        # PW Sucks
        data = data.apply(to_numeric, errors = 'ignore')

        return data

    def upload(self, df) -> bool:

        #TODO Put df in PW format

        self.esa.change_and_confirm_params_multiple_element(
            ObjectType = 'TSContingency',
            command_df = DataFrame({'TSCTGName': ['SimOnly']})#, 'SchedValue': [baseLoad]})
        )
        
        # TODO return success
        return True
    
    def skipallbut(self, ctgs):

        df = self.esa.GetParametersMultipleElement(
            'tscontingency',
            ['TSCTGName'],
        )
        
        # Assign
        names = [ctg.TSCTGName for ctg in ctgs]
        df['CTGSkip'] = 'YES'
        df.loc[df['TSCTGName'].isin(names), 'CTGSkip'] = 'NO'

        self.esa.change_and_confirm_params_multiple_element(
            ObjectType = 'TSContingency',
            command_df = df
        )