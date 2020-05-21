format:
	black ./clutchless

clean-docker:
	docker stop $(docker ps -a -q)
	docker rm $(docker ps -a -q)

install:
	poetry build && pip install --force-reinstall dist/clutchless-0.1.0.dev0-py3-none-any.whl

image:
	docker build -f docker/clutchless.df -t clutchless .

shell: image
	docker run --rm -it clutchless

test: image
	docker run --rm clutchless sh -c "python -i client_setup.py"
