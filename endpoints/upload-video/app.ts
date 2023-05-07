import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
import { PutObjectCommand, S3Client } from '@aws-sdk/client-s3';

/**
 *
 * Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format
 * @param {Object} event - API Gateway Lambda Proxy Input Format
 *
 * Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
 * @returns {Object} object - API Gateway Lambda Proxy Output Format
 *
 */

const client = new S3Client({});
export const lambdaHandler = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
    console.log(`Starting at: ${new Date()}`);
    try {
        console.log({ event });
        const contentType = event.headers?.['Content-Type'] ?? 'vido/mp4';
        console.log({ contentType });
        const videoBase64 = event.body as string;
        if (!videoBase64) {
            return {
                statusCode: 400,
                body: JSON.stringify({ message: 'No video data provided' }),
            };
        }
        const fileName =
            event.queryStringParameters?.['fileName'] ??
            event.queryStringParameters?.['filename'] ??
            `vid_uploaded_${new Date().getTime()}.mp4`;
        const command = new PutObjectCommand({
            Bucket: 'radar-speed-sign',
            Key: fileName,
            Body: Buffer.from(videoBase64, 'base64'),
            ContentType: contentType,
            Metadata: { contentType },
        });
        console.log({ command });
        await client.send(command);
        return {
            statusCode: 200,
            body: JSON.stringify({
                message: `Successfully uploaded ${fileName}`,
            }),
        };
    } catch (err) {
        console.log('an error occurred:', err);
        return {
            statusCode: 500,
            body: JSON.stringify({
                message: `Error: ${err}`,
            }),
        };
    }
};
