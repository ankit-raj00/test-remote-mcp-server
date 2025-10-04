from fastmcp import FastMCP
import random
import json

mcp = FastMCP("simple calculator")

@mcp.tool
def add(a:int , b:int) ->int:
    """Add Two numbers together
    Args:
        a : First number
        b : Second number
        
    Return :
            The sum of a and b
    """
    
    return a + b

@mcp.tool
def random_number(min_val : int , max_val : int = 100) -> int:
    """Generate a random number within a range.
    Args:
        min_val : Minimum value (default : 1)
        max_val : Maximum value (default : 100)
        
    Returns : 
        A random integer between min_val and max_val
    """
    return random.randint(min_val , max_val)
    
@mcp.resource("info://server")
def server_info() -> str:
    """Get information about this server."""
    
    info = {
        "name" : "Simple Calculator Server.",
        "Version" : "1.0.0",
        "description" : "A basic MCP Server with math tools",
        "tools" : ["add" , "random_number"],
        "author" : "Your Name"
    }
    
    return json.dumps(info , indent=2)

if __name__ == "__main__":
    mcp.run(transport="http" , host="0.0.0.0" , port=8000)
    # mcp.run() was only for local server
    