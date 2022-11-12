import yaml

CONFIG_FILENAME = "config.yaml"

class Config:
    def __init__(self) -> None:
        self._config = {}
        self.read_file()

    def read_file(self) -> None:
        with open(CONFIG_FILENAME, 'r') as stream:
            self._config = yaml.safe_load(stream)
    
    def get(self, param_name: str = "", default_value: any = None) -> any:
        if param_name.find(".") > 0:
            local_config = self._config
            for item in param_name.split("."):
                if local_config[item]:
                    local_config = local_config[item]
                else:
                    return default_value
            return local_config

        return self._config[param_name] if self._config[param_name] else default_value
    
    def get_all(self) -> dict:
        return self._config

    def set(self, param_name: str, value: any = None):
        if param_name == None:
            raise RuntimeError("Params must have a name")
        
        self._config[param_name] = value
