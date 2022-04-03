
var MINECRAFT_PORT = "8252";
var MINECRAFT_LOG_LINES_LOADED = 44;

var App = function ()
{
    this.responseText = document.getElementById("responseText");

    this.minecraftStatusButton = document.getElementById("minecraftStatusButton");
    this.minecraftOutputButton = document.getElementById("minecraftOutputButton");
    this.minecraftStopButton = document.getElementById("minecraftStopButton");
    this.minecraftResponseText = document.getElementById("minecraftResponseText");

    this.instanceAddress = "";

    this.serverStartPollInterval = 0;
    this.serverStatusPollInterval = 0;
    this.minecraftPollInterval = 0;
    this.maxAttempts = 99;
    this.attempts = 0;

    this.waitForShutdown = false;

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
    if (this.serverStartPollInterval)
    {
        return;
    }
    this.waitForShutdown = false;

    window.clearInterval(this.serverStatusPollInterval);
    this.serverStatusPollInterval = 0;

    this.attempts = 0;
    this.startServerPoll();
    this.serverStartPollInterval = window.setInterval(this.startServerPoll.bind(this), 7000);
};

App.prototype.tryPoll = function ()
{
    this.attempts += 1;
    if (this.attempts > this.maxAttempts)
    {
        window.clearInterval(that.serverStartPollInterval);
        window.clearInterval(that.serverStatusPollInterval);
        window.clearInterval(that.minecraftPollInterval);
        that.serverStartPollInterval = 0;
        that.serverStatusPollInterval = 0;
        that.minecraftPollInterval = 0;
        return false;
    }
    return true;
};

App.prototype.startServerPoll = function ()
{
    if (!this.tryPoll())
    {
        return;
    }
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
                window.clearInterval(that.serverStartPollInterval);
                that.serverStartPollInterval = 0;

                that.getMinecraftStatus();
            }
        }
    });
};

App.prototype.getStatus = function ()
{
    if (this.serverStartPollInterval || this.serverStatusPollInterval)
    {
        return;
    }
    this.attempts = 0;
    this.serverStatusPoll();
    this.serverStatusPollInterval = window.setInterval(this.serverStatusPoll.bind(this), 7000);
};

App.prototype.serverStatusPoll = function ()
{
    if (!this.tryPoll())
    {
        return;
    }
    this.responseText.value = "Sending request...";
    var that = this;
    this.makeRequest('/test', function (response)
    {
        var data = JSON.parse(response);
        var str = JSON.stringify(data, null, 2);
        that.responseText.value = str;
        that.instanceAddress = data.server.PublicIpAddress;
        that.enableMinecraft(that.instanceAddress);
        if ((data.status == "STOPPED" && !that.instanceAddress) || (!this.waitForShutdown && that.instanceAddress && data.status == "SPOT_CREATED"))
        {
            window.clearInterval(that.serverStatusPollInterval);
            that.serverStatusPollInterval = 0;
        }
    });
};

App.prototype.minecraftPoll = function ()
{
    if (!this.tryPoll())
    {
        return;
    }
    this.minecraftResponseText.value = "Sending request...";
    var that = this;
    if (this.instanceAddress)
    {
        this.makeRequest('/msg-server?msg=status', function (response)
        {
            var data = JSON.parse(response);
            var str = JSON.stringify(data, null, 2);
            if (data.minecraft)
            {
                if (data.minecraft.status == "RUNNING")
                {
                    window.clearInterval(that.minecraftPollInterval);
                    that.minecraftPollInterval = 0;
                }
                else if (data.minecraft.status == "LOADING" && data.minecraft.lines_output < MINECRAFT_LOG_LINES_LOADED)
                {
                    str = "Minecraft startup " + Math.floor((data.minecraft.lines_output / MINECRAFT_LOG_LINES_LOADED) * 100) + "%\n\n" + str;
                }
            }
            else if (data.error == "NO_MINECRAFT_SERVER")
            {
                window.clearInterval(that.minecraftPollInterval);
                that.minecraftPollInterval = 0;

                that.getStatus();
            }
            that.minecraftResponseText.value = str;
        });
    }
};

App.prototype.getMinecraftStatus = function ()
{
    if (this.minecraftPollInterval)
    {
        return;
    }
    this.attempts = 0;
    this.minecraftPoll();
    this.minecraftPollInterval = window.setInterval(this.minecraftPoll.bind(this), 7000);
};

App.prototype.getMinecraftOutput = function ()
{
    window.clearInterval(this.minecraftPollInterval);
    this.minecraftPollInterval = 0;

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
    this.waitForShutdown = true;

    this.minecraftResponseText.value = "Sending request...";
    var that = this;
    this.makeRequest('/msg-server?msg=stop-server', function (response)
    {
        var data = JSON.parse(response);
        var str = JSON.stringify(data, null, 2);
        that.minecraftResponseText.value = str;

        window.setTimeout(function () {
            if (!that.minecraftPollInterval)
            {
                that.minecraftPoll();
            }
            that.getStatus();
        }, 7000);
    });
};

var app = new App();

