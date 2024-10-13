cmake_minimum_required(VERSION 3.29)
project(cpp)

set(CMAKE_CXX_STANDARD 26)

find_package(asio CONFIG REQUIRED)
target_link_libraries(main PRIVATE asio::asio)

add_executable(cpp main.cpp)
