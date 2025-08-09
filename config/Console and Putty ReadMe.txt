Console command:
+ For activating the virtual enviroment: source ~/venvs/trailmate/bin/activate
+ For running and checking the agent: python mcp_client.py
+ To install langchain: pip install langchain-community
+ To install community langchain dependency:pip install langchain-community
+ To install community langchain depedency (if depreacated previos option): pip install -U langchain-community
+ For running the Streamlit App: streamlit run app.py

Streanlit:
+If links are generated, but they do not load, check terminal output from Streamlit:streamlit run app.py --server.enableCORS false --server.enableXsrfProtection false --server.headless true --server.port 8501
+If links were generated but they do not load correctly, check the ports in putty for the instance:Source port: 8501, Destination: localhost:8501

These are the packges we need to install:
streamlit
python-dotenv
requests
langchain
langchain-openai
langchain-core
pandas

