
#include <iostream>
#include <nlohmann/json.hpp>
#include <moteus/moteus.h>
#include <chrono>
#include <thread>
#include <unordered_map>
#include <memory>
#include <future>
#include <asio.hpp>


using namespace std;
using json = nlohmann::json;
using asio::ip::tcp;

std::string address = "localhost";
int port = 5135;

// Controllers with IDs
std::unordered_map<int, std::shared_ptr<moteus::Controller>> controllers = {
    {1, std::make_shared<moteus::Controller>(moteus::Controller(1))},
    {2, std::make_shared<moteus::Controller>(moteus::Controller(2))}
};

std::unordered_map<int, std::optional<double>> last_poses;

// Function to parse commands
std::unordered_map<int, json> parse_commands(const std::string& data) {
    std::unordered_map<int, json> commands;
    json default_commands = {
        {"id", nullptr},
        {"p", 0.0},
        {"d", true}
    };

    try {
        json json_data = json::parse(data);
        for (const auto& item : json_data) {
            int motor_id = item["id"];
            if (commands.find(motor_id) == commands.end()) {
                commands[motor_id] = default_commands;
            }
            for (auto& [key, value] : item.items()) {
                commands[motor_id][key] = value;
            }
        }
    } catch (json::parse_error& e) {
        std::cerr << "JSON parse error: " << e.what() << std::endl;
    }

    return commands;
}

// Handle client connection
void handle_client(tcp::socket socket) {
    try {
        asio::streambuf buffer;
        asio::read_until(socket, buffer, "\n\n");

        std::istream is(&buffer);
        std::string data;
        std::getline(is, data);

        if (data.empty()) {
            std::cout << "No data received" << std::endl;
            return;
        }

        auto commands = parse_commands(data);
        std::vector<json> responses;

        for (const auto& [_, command] : commands) {
            int cid = command["id"];
            if (controllers.find(cid) != controllers.end()) {
                if (command["d"].get<bool>()) {
                    last_poses[cid] = command["p"].get<double>();
                }

                auto state = controllers[cid]->Query();

                json response = {
                    {"id", cid},
                    {"ep", state.position},
                    {"v", state.velocity},
                    {"t", state.torque},
                    {"vo", state.voltage},
                    {"te", state.temperature}
                };
                responses.push_back(response);
            }
        }

        json response_json = responses;
        std::string response_str = response_json.dump() + "\n\n";
        asio::write(socket, asio::buffer(response_str));

    } catch (const std::exception& e) {
        std::cerr << "Unexpected error: " << e.what() << std::endl;
    }
}

// Control loop function
void control_loop() {
    auto start_time = std::chrono::steady_clock::now();
    int frame_count = 0;

    while (true) {
        for (const auto& [cid, controller] : controllers) {
            if (last_poses[cid]) {
                controller->SetPosition(last_poses[cid].value(), true);
            }
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(1));
        frame_count++;

        auto elapsed_time = std::chrono::steady_clock::now() - start_time;
        if (elapsed_time >= std::chrono::seconds(1)) {
            double fps = frame_count / std::chrono::duration<double>(elapsed_time).count();
            std::cout << "FPS: " << fps << std::endl;
            frame_count = 0;
            start_time = std::chrono::steady_clock::now();
        }
    }
}

// Main server function
void server(asio::io_context& io_context) {
    tcp::acceptor acceptor(io_context, tcp::endpoint(tcp::v4(), port));

    while (true) {
        tcp::socket socket(io_context);
        acceptor.accept(socket);

        std::thread(handle_client, std::move(socket)).detach();
    }
}

int main() {
    try {
        asio::io_context io_context;

        // Start the control loop in a separate thread
        std::thread control_thread(control_loop);

        // Start the server
        std::cout << "Server started at " << address << ":" << port << std::endl;
        server(io_context);

        control_thread.join();
    } catch (std::exception& e) {
        std::cerr << "Server crashed with error: " << e.what() << std::endl;
        std::cerr << "Restarting server..." << std::endl;
        main();  // Restart the server on crash
    }

    return 0;
}
