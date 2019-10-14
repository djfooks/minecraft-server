
var MINECRAFT_PORT = "8252";
var MINECRAFT_LOG_LINES_LOADED = 6790;

var App = function ()
{
    this.responseText = document.getElementById("responseText");

    this.minecraftStatusButton = document.getElementById("minecraftStatusButton");
    this.minecraftOutputButton = document.getElementById("minecraftOutputButton");
    this.minecraftStopButton = document.getElementById("minecraftStopButton");
    this.minecraftResponseText = document.getElementById("minecraftResponseText");

    this.instanceAddress = "";

    this.startPollInterval = 0;

    this.enableMinecraft(false);
    this.getStatus();
};

App.prototype.enableMinecraft = function (v)
{
    this.minecraftStatusButton.disabled = !v;
    this.minecraftOutputButton.disabled = !v;
    this.minecraftStopButton.disabled = !v;
};

App.prototype.getApiKey = function ()
{
    if (this.apiKey)
    {
        return this.apiKey;
    }

    var apiKey = window.localStorage.getItem("api-key");
    if (!apiKey)
    {
        apiKey = prompt("API KEY");
        window.localStorage.setItem("api-key", apiKey);
    }
    this.apiKey = apiKey;
    return apiKey;
};

App.prototype.clearApiKey = function ()
{
    window.localStorage.removeItem("api-key");
};

App.prototype.makeRequest = function (url, cb)
{
    var apiKey = this.getApiKey();

    var that = this;
    var xhr = new XMLHttpRequest();
    function reqListener ()
    {
        try
        {
            var data = JSON.parse(xhr.response);
            if (data.error == "API_KEY_FAIL")
            {
                this.clearApiKey();
            }
        }
        catch (e)
        {
        }
        cb(xhr.response);
    }

    xhr.onload = reqListener;
    xhr.open("GET", 'https://if39zuadqc.execute-api.eu-west-2.amazonaws.com/default' + url);
    xhr.setRequestHeader("Content-Type", "text/plain");
    xhr.setRequestHeader("api-key", apiKey);
    xhr.send();
};

App.prototype.startServer = function ()
{
    this.startPollInterval = window.setInterval(this.startServerPoll.bind(this), 5000);
    this.startServerPoll();
};

App.prototype.startServerPoll = function ()
{
    this.responseText.value = "Sending request...";
    var that = this;
    this.makeRequest('/start-server', function (response)
    {
        var data = JSON.parse(response);
        var str = JSON.stringify(data, null, 2);
        that.responseText.value = str;
        if (data.server)
        {
            that.instanceAddress = data.server.PublicIpAddress;
            that.enableMinecraft(that.instanceAddress);
            if (that.instanceAddress && data.status == "SPOT_CREATED")
            {
                window.clearInterval(that.startPollInterval);
                that.startPollInterval = 0;
            }
        }
    });
};

App.prototype.getStatus = function ()
{
    this.responseText.value = "Sending request...";
    var that = this;
    this.makeRequest('/test', function (response)
    {
        var data = JSON.parse(response);
        var str = JSON.stringify(data, null, 2);
        that.responseText.value = str;
        that.instanceAddress = data.server.PublicIpAddress;
        that.enableMinecraft(that.instanceAddress);
    });
};

App.prototype.getMinecraftStatus = function ()
{
    this.minecraftResponseText.value = "Sending request...";
    var that = this;
    if (this.instanceAddress)
    {
        this.makeRequest('/msg-server?msg=status', function (response)
        {
            var data = JSON.parse(response);
            var str = JSON.stringify(data, null, 2);
            if (!data.error)
            {
                if (data.minecraft.lines_output >= MINECRAFT_LOG_LINES_LOADED)
                {
                    str = "Minecraft running...\n\n" + str;
                }
                else
                {
                    str = "Minecraft startup " + Math.floor((data.minecraft.lines_output / MINECRAFT_LOG_LINES_LOADED) * 100) + "%\n\n" + str;
                }
            }
            that.minecraftResponseText.value = str;
        });
    }
};

App.prototype.getMinecraftOutput = function ()
{
    this.minecraftResponseText.value = "Sending request...";
    var that = this;
    if (this.instanceAddress)
    {
        this.makeRequest('/msg-server?msg=output', function (response)
        {
            that.minecraftResponseText.value = response;
        });
    }
};

App.prototype.stopMinecraft = function ()
{
    this.minecraftResponseText.value = "Sending request...";
    var that = this;
    this.makeRequest('/msg-server?msg=stop-server', function (response)
    {
        var data = JSON.parse(response);
        var str = JSON.stringify(data, null, 2);
        that.minecraftResponseText.value = str;
    });
};

var app = new App();

