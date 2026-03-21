import subprocess
import shlex

def run_command(command, shell=False):
    try:
        if not shell:
            cmd_list = shlex.split(command)
        else:
            cmd_list = command
        result = subprocess.run(cmd_list, shell=shell, capture_output=True, text=True, timeout=30)
        output = result.stdout[:4000]
        error = result.stderr[:4000]
        response = ''
        if output:
            response += f"Output:\n{output}\n"
        if error:
            response += f"Error:\n{error}\n"
        return response if response else "Command executed successfully with no output."
    except Exception as e:
        return str(e)

print(run_command('figlet "test"', shell=True))
