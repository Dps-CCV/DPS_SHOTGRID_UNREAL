def main():
  import shotgun_api3
  import os
  sg = shotgun_api3.Shotgun("https://dareplanet.shotgunstudio.com",
                          script_name="GithubUpdateConfig",
                          api_key=os.environ['UPDATECONFIGKEY'])
  data = {'descriptor': "sgtk:descriptor:git_branch?branch="+os.environ['BRANCH']+"&path=https://github.com/Dps-CCV/DPS_SHOTGRID_UNREAL.git&version="+os.environ['NEWCODE']}
  id = 2509
  print(data)
  sg.update('PipelineConfiguration', id, data)



if __name__ == '__main__':
  main()
