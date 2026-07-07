FROM ubuntu:latest

# Install figlet
RUN apt-get update && apt-get install -y figlet

# Copy and setup the script
COPY ./print_message.sh /app/print_message.sh
# make the script executable 
RUN chmod +x /app/print_message.sh 

# set the script as the default command to run when the container starts
CMD [ "/app/print_message.sh" ]