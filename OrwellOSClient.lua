--[[
This is a lua client for the OrwellOS for CC:Tweaked
It is a simple client that connects to the OrwellOS server through
an ssl websocket connection and updates the server with its current
status. It gets orders from the server and executes them.
--]]

-- Variables
local serverAddress = "wss://CHANGEME:8080"

-- Functions
function printError(message)
    print("[ERROR] " .. message)
end

function getComputerType()
    local computerType = 0
    if turtle then
        if term.isColor() then
            computerType = 3 -- Advanced Turtle
        else
            computerType = 1 -- Turtle
        end
    else
        if term.isColor() then
            computerType = 2 -- Advanced Computer
        else
            computerType = 0 -- Computer
        end
    end
    return computerType
end

function identify(ws)
    local computerName = os.getComputerLabel()
    if computerName == nil then
        -- Chose two random names
        computerName = ComputerNames[math.random(#ComputerNames)] .. " " .. ComputerNames[math.random(#ComputerNames)]
        os.setComputerLabel(computerName)
    end
    local data = {
        ["computerName"] = computerName,
        ["osVersion"] = os.version(),
        ["computerID"] = os.getComputerID(),
        ["computerType"] = getComputerType()
    }
    ws.send(textutils.serializeJSON(data))
end

function runArbitraryCode(ws, code)
    local func, err = loadstring(code)
    if not func then
        printError("Failed to load code: " .. err)
        ws.send("Failed to load code: " .. err)
    else
        local result = func()
        ws.send("Code executed successfully: " .. result)
    end
end

local ComputerNames = {
    "Ada", "Babbage", "Colossus", "Dijkstra", "Enigma", "Feynman", "Gauss", "Hopper", "Ivan", "Joule", "Kolmogorov", "Lovelace", "Mandelbrot", "Newton", "Orwell", "Pascal", "Quine", "Ramanujan", "Shannon", "Turing", "Ulam", "von Neumann", "Wozniak", "Xenakis", "Yoneda", "Zuse"
}

local orders = {
    ["runArbitraryCode"] = runArbitraryCode,
    ["identify"] = identify
}

-- Main loop
while true do
    local ws, err = http.websocket(serverAddress)
    if not ws then
        printError("Failed to connect to server: " .. err)
        sleep(5)
    elseif ws.receive() == "Hello" then
        print("Connected to server")
        local computerName = os.getComputerLabel()
        if computerName == nil then
            -- Chose two random names
            computerName = ComputerNames[math.random(#ComputerNames)] .. " " .. ComputerNames[math.random(#ComputerNames)]
            os.setComputerLabel(computerName)
        end
        ws.send("Hello " .. computerName .. " on OrwellOS")
        while true do
            local message = ws.receive()
            if message == nil then
                print("Server closed connection")
                break
            else
                local orderJson = textutils.unserializeJSON(message)
                print("Received order: " .. orderJson["order"])
                local order = orderJson["order"]
                if orders[order] ~= nil then
                    orders[order](ws, orderJson["data"])
                else
                    printError("Invalid order: " .. order)
                    ws.send("Invalid order: " .. order)
                end
            end
        end
    else
        printError("Server did not respond with hello")
        sleep(5)
    end
end